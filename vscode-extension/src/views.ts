// Tree views: Clients and Tasks. Every label comes from wai output or the user's settings, shown as plain text.

import * as vscode from 'vscode';
import { CLIENT_NAMES, ClientState } from './clients';
import { isTaskId, plainText } from './text';

export interface TaskRow {
  id: string;
  client?: string;
  status?: string;
  lastCheckpoint?: string;
  nextAction?: string;
  taskFile?: string;
  error?: string;
}

export function readTasks(payload: Record<string, unknown>): TaskRow[] {
  const rows = Array.isArray(payload.tasks) ? payload.tasks : [];
  return rows
    .filter((t) => isTaskId(t?.id))
    .map((t) => ({
      id: t.id,
      client: typeof t.client === 'string' ? t.client : undefined,
      status: typeof t.status === 'string' ? t.status : undefined,
      lastCheckpoint: typeof t.last_checkpoint === 'string' ? t.last_checkpoint : undefined,
      nextAction: typeof t.next_action === 'string' ? t.next_action : undefined,
      taskFile: typeof t.task_file === 'string' ? t.task_file : undefined,
      error: typeof t.error === 'string' ? t.error : undefined,
    }));
}

abstract class ListProvider<T> implements vscode.TreeDataProvider<T> {
  private readonly changed = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.changed.event;
  protected items: T[] = [];

  set(items: T[]): void {
    this.items = items;
    this.changed.fire();
  }

  getChildren(element?: T): T[] {
    return element ? [] : this.items;
  }

  abstract getTreeItem(element: T): vscode.TreeItem;
}

export class TasksProvider extends ListProvider<TaskRow> {
  getTreeItem(task: TaskRow): vscode.TreeItem {
    const item = new vscode.TreeItem(task.id);
    if (task.error) {
      item.description = vscode.l10n.t('unreadable');
      item.tooltip = plainText(task.error, 500);
      item.iconPath = new vscode.ThemeIcon('warning');
      return item;
    }
    item.description = `${plainText(task.client, 20)} · ${plainText(task.status, 20)}`;
    item.tooltip = [
      vscode.l10n.t('Client: {0}', plainText(task.client, 20)),
      vscode.l10n.t('Status: {0}', plainText(task.status, 20)),
      vscode.l10n.t('Last checkpoint: {0}', task.lastCheckpoint ? plainText(task.lastCheckpoint, 60) : vscode.l10n.t('none')),
      vscode.l10n.t('Next action: {0}', plainText(task.nextAction, 300) || '-'),
    ].join('\n');
    item.iconPath = new vscode.ThemeIcon('tasklist');
    item.contextValue = 'workshopAi.task';
    item.command = { command: 'workshopAi.openTask', title: vscode.l10n.t('Open task'), arguments: [task.id] };
    return item;
  }
}

export class ClientsProvider extends ListProvider<ClientState> {
  getTreeItem(client: ClientState): vscode.TreeItem {
    const item = new vscode.TreeItem(CLIENT_NAMES[client.id]);
    const confirmed = client.confirmed ? vscode.l10n.t('confirmed') : vscode.l10n.t('not confirmed');
    item.description = `${client.source} · ${confirmed}`;
    item.tooltip = client.path ? plainText(client.path, 500) : vscode.l10n.t('Not found on PATH.');
    item.iconPath = new vscode.ThemeIcon(client.source === 'not found' ? 'circle-slash'
      : client.confirmed ? 'pass' : 'question');
    return item;
  }
}
