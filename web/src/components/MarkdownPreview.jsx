import { parseMarkdown } from '../markdown.js';

function InlineContent({ tokens }) {
  return tokens.map((token, index) => {
    switch (token.type) {
      case 'strong':
        return <strong key={index}><InlineContent tokens={token.children} /></strong>;
      case 'em':
        return <em key={index}><InlineContent tokens={token.children} /></em>;
      case 'del':
        return <del key={index}><InlineContent tokens={token.children} /></del>;
      case 'code':
        return <code key={index}>{token.value}</code>;
      case 'image':
        return <span key={index} className="markdown-image-label">[Imagen: {token.value}]</span>;
      case 'link':
        return token.href
          ? <a key={index} href={token.href} target="_blank" rel="noopener noreferrer">{token.value}</a>
          : <span key={index}>{token.value}</span>;
      default:
        return <span key={index}>{token.value}</span>;
    }
  });
}

function MarkdownBlock({ block, index }) {
  switch (block.type) {
    case 'heading': {
      const Tag = `h${block.level}`;
      return <Tag key={index}><InlineContent tokens={block.children} /></Tag>;
    }
    case 'paragraph':
      return <p key={index}><InlineContent tokens={block.children} /></p>;
    case 'quote':
      return <blockquote key={index}>{block.children.map((child, childIndex) =>
        <MarkdownBlock key={childIndex} block={child} index={childIndex} />)}</blockquote>;
    case 'code-block':
      return <pre key={index}><code>{block.value}</code></pre>;
    case 'rule':
      return <hr key={index} />;
    case 'list': {
      const Tag = block.ordered ? 'ol' : 'ul';
      return <Tag key={index}>{block.items.map((item, itemIndex) =>
        <li key={itemIndex}><InlineContent tokens={item} /></li>)}</Tag>;
    }
    case 'table':
      return <div key={index} className="markdown-table-wrap"><table>
        <thead><tr>{block.headers.map((cell, cellIndex) =>
          <th key={cellIndex} scope="col"><InlineContent tokens={cell} /></th>)}</tr></thead>
        <tbody>{block.rows.map((row, rowIndex) =>
          <tr key={rowIndex}>{row.map((cell, cellIndex) =>
            <td key={cellIndex}><InlineContent tokens={cell} /></td>)}</tr>)}</tbody>
      </table></div>;
    default:
      return null;
  }
}

export default function MarkdownPreview({ source }) {
  const blocks = parseMarkdown(source);
  return <article className="markdown-preview">
    {blocks.length ? blocks.map((block, index) => <MarkdownBlock key={index} block={block} index={index} />)
      : <p className="markdown-empty">Documento vacío.</p>}
  </article>;
}
