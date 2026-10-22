"""Bounded search across Workshop resources, saved conversations and file versions."""
from __future__ import annotations

import conversation_store
import document_versions
import resource_interaction
import workshop_data

MAX_QUERY_LENGTH = 200
MAX_RESULTS = 100
MAX_SCANNED_BYTES = 16 * 1024 * 1024
MAX_RESOURCES = 2000
EXCERPT_LENGTH = 180


def _query_terms(query: str) -> list[list[str]]:
    words = workshop_data.query_words(query)
    if len(words) > 8:
        raise ValueError('Usa como máximo ocho palabras en la búsqueda.')
    return [[word, *workshop_data.SEARCH_SYNONYMS.get(word, [])] for word in words]


def _matches(text: str, terms: list[list[str]]) -> bool:
    normalized = workshop_data.remove_diacritics(text)
    return all(any(workshop_data.word_matches(normalized, option) for option in choices)
               for choices in terms)


def _excerpt(text: str, terms: list[list[str]]) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates = [option for choices in terms for option in choices]
    for line in lines:
        normalized = workshop_data.remove_diacritics(line)
        if any(workshop_data.word_matches(normalized, term) for term in candidates):
            compact = ' '.join(line.split())
            return compact if len(compact) <= EXCERPT_LENGTH else compact[:EXCERPT_LENGTH - 1] + '…'
    compact = ' '.join(text.split())
    return compact if len(compact) <= EXCERPT_LENGTH else compact[:EXCERPT_LENGTH - 1] + '…'


def search(snapshot, body: dict) -> dict:
    query = body.get('query') if isinstance(body, dict) else None
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_LENGTH:
        return dict(ok=False, message='Escribe una búsqueda de hasta 200 caracteres.')
    try:
        terms = _query_terms(query)
    except ValueError as error:
        return dict(ok=False, message=str(error))
    if not terms:
        return dict(ok=False, message='Escribe una búsqueda.')

    results = []
    scanned_bytes = 0
    scanned_resources = 0
    skipped = 0
    partial = False
    for item_id, resource in snapshot.by_id.items():
        if (scanned_resources >= MAX_RESOURCES or scanned_bytes >= MAX_SCANNED_BYTES
                or len(results) >= MAX_RESULTS):
            partial = True
            break
        scanned_resources += 1
        try:
            path, relative = resource_interaction.safe_path(snapshot, {'id': item_id})
            if not resource_interaction.eligible(relative):
                continue
        except (resource_interaction.ResourceError, OSError, UnicodeError, ValueError):
            skipped += 1
            continue
        try:
            current_size = path.stat().st_size
            if current_size > MAX_SCANNED_BYTES - scanned_bytes:
                partial = True
                break
            if current_size > resource_interaction.MAX_TEXT_BYTES:
                skipped += 1
                text = ''
            else:
                raw = resource_interaction.read_bytes(path, resource_interaction.MAX_TEXT_BYTES)
                scanned_bytes += len(raw)
                text = raw.decode('utf-8-sig')
        except (resource_interaction.ResourceError, OSError, UnicodeError, ValueError):
            skipped += 1
            text = ''
        metadata = getattr(resource, 'search_text', '')
        searchable = f'{metadata}\n{text}'
        if _matches(searchable, terms) and (text or _matches(metadata, terms)):
            results.append(dict(kind='resource', item_id=item_id, title=resource.title or resource.name,
                                section=resource.section, path=relative.as_posix(),
                                excerpt=_excerpt(text if _matches(text, terms) else metadata, terms),
                                modified=resource.modified.isoformat() if resource.modified else ''))
        try:
            versions = document_versions.list_versions(snapshot.workshop_root, relative.as_posix())
        except (OSError, ValueError):
            skipped += 1
            continue
        for version in versions:
            if len(results) >= MAX_RESULTS or scanned_bytes >= MAX_SCANNED_BYTES:
                partial = True
                break
            if version['size'] > MAX_SCANNED_BYTES - scanned_bytes:
                partial = True
                break
            try:
                raw_version = document_versions.read_version(
                    snapshot.workshop_root, relative.as_posix(), version['version_id'])
                scanned_bytes += len(raw_version)
                version_text = raw_version.decode('utf-8-sig')
            except (OSError, ValueError, UnicodeError):
                skipped += 1
                continue
            if _matches(version_text, terms):
                results.append(dict(kind='version', item_id=item_id, title=resource.title or resource.name,
                                    section=resource.section, path=relative.as_posix(),
                                    version_id=version['version_id'], modified=version['created_at'],
                                    excerpt=_excerpt(version_text, terms)))

    try:
        conversations, conversation_skipped, conversation_bytes, conversation_partial = (
            conversation_store.searchable_conversations(snapshot, MAX_SCANNED_BYTES - scanned_bytes))
        partial = partial or conversation_partial
    except (OSError, ValueError):
        conversations, conversation_skipped, conversation_bytes = [], 1, 0
    scanned_bytes += conversation_bytes
    skipped += conversation_skipped
    for record in conversations:
        if len(results) >= MAX_RESULTS:
            partial = True
            break
        for message in record['messages']:
            content = message['content']
            if _matches(content, terms):
                results.append(dict(kind='conversation', conversation_id=record['id'],
                                    title=conversation_store._summary(record)['title'],
                                    modified=record['updated_at'], excerpt=_excerpt(content, terms)))
                break

    results.sort(key=lambda result: result.get('modified', ''), reverse=True)
    return dict(ok=True, query=query.strip(), results=results[:MAX_RESULTS], partial=partial,
                skipped=skipped, scanned_resources=scanned_resources, scanned_bytes=scanned_bytes)
