// Workshop AI extension, increment E1 (docs/vscode-extension-e1-plan.md): client detection, infra reuse, Tasks
// view, task creation and context through wai. All state changes go through wai; this file writes no state.

import * as os from 'node:os';
import * as path from 'node:path';
import * as vscode from 'vscode';
import {
  CLIENT_IDS, CLIENT_NAMES, ClientId, ClientState, ConfirmedClient, clientStates, detectClients, isFile, readConfirmed,
} from './clients';
import { locateInfra } from './infra';
import { isTaskId, plainText, TASK_ID_RE } from './text';
import { ClientsProvider, readTasks, TaskRow, TasksProvider } from './views';
import { checkWai, findPython, findWaiFolder, runWai, WaiConfig, WaiFailure } from './wai';

type State = 'loading' | 'noWai' | 'noFolder' | 'noProject' | 'error' | 'ready';

let log: vscode.LogOutputChannel;
const tasksView = new TasksProvider();
const clientsView = new ClientsProvider();
let extensionPath = '';
let cfg: WaiConfig | undefined;
let checkedConfig = '';
let failedConfig = '';
let projectRoot: string | undefined;
let state: State = 'loading';
let clients: ClientState[] = [];
let tasks: TaskRow[] = [];
let infraWarned = '';
let refreshing: Promise<void> | undefined;
let refreshAgain = false;
let watcher: vscode.Disposable | undefined;

function settings(): vscode.WorkspaceConfiguration {
  return vscode.workspace.getConfiguration('workshopAi');
}

// Machine-scoped settings (EXT-09): read only the user-level value, so a workspace file cannot redirect it.
function machineSetting(key: string): string | undefined {
  const value = settings().inspect<string>(key)?.globalValue;
  return typeof value === 'string' && value.trim() ? value.trim() : undefined;
}

async function setState(next: State): Promise<void> {
  state = next;
  await vscode.commands.executeCommand('setContext', 'workshopAi.state', next);
}

function showFailure(error: unknown): void {
  const message = error instanceof WaiFailure ? error.message : vscode.l10n.t('Unexpected error: {0}', String(error));
  // The log keeps the exit code only: wai messages can repeat file names or task text (spec section 8.2).
  log.error(error instanceof WaiFailure ? `failure, exit ${error.code ?? 'none'}` : 'unexpected error');
  void vscode.window.showErrorMessage(plainText(message, 500));
}

// Spec section 8.6: the manifest already keeps the extension off in Restricted Mode; this is a second guard.
function trusted(): boolean {
  if (!vscode.workspace.isTrusted) {
    void vscode.window.showWarningMessage(vscode.l10n.t('Workshop AI works only in a trusted workspace.'));
  }
  return vscode.workspace.isTrusted;
}

function refreshClients(): void {
  const confirmed = readConfirmed(settings().inspect('clients')?.globalValue);
  clients = clientStates(confirmed, detectClients(process.env));
  clientsView.set(clients);
}

async function resolveWai(): Promise<WaiConfig | undefined> {
  const infra = locateInfra(machineSetting('infraPath'), process.env, os.homedir());
  if (infra.problem && infraWarned !== infra.path) {
    infraWarned = infra.path;
    void vscode.window.showWarningMessage(vscode.l10n.t(
      'Shared infrastructure not usable at {0} ({1}: {2}). Set workshopAi.infraPath in your user settings. Cloning it from the extension is not available yet.',
      infra.path, infra.source, infra.problem));
  }
  const waiPath = findWaiFolder(machineSetting('waiPath'), extensionPath);
  const python = findPython(machineSetting('pythonPath'), process.env);
  if (!waiPath || !python) {
    log.warn(`wai folder ${waiPath ? 'found' : 'not found'}, python ${python ? 'found' : 'not found'}`);
    return undefined;
  }
  const next = { python, waiPath, infra: infra.path };
  const key = JSON.stringify(next);
  if (key === failedConfig) {
    return undefined; // already reported; retried only after a settings change or a manual Refresh (J7f)
  }
  if (key !== checkedConfig) {
    try {
      log.info(await checkWai(next));
    } catch (error) {
      failedConfig = key;
      throw error;
    }
    checkedConfig = key;
  }
  return next;
}

async function doRefresh(): Promise<void> {
  if (!vscode.workspace.isTrusted) {
    return;
  }
  try {
    refreshClients();
    cfg = await resolveWai();
  } catch (error) {
    cfg = undefined;
    showFailure(error);
  }
  if (!cfg) {
    tasksView.set([]);
    await setState('noWai');
    return;
  }
  projectRoot = vscode.workspace.workspaceFolders?.find((f) => f.uri.scheme === 'file')?.uri.fsPath;
  if (!projectRoot) {
    tasksView.set([]);
    await setState('noFolder');
    return;
  }
  try {
    tasks = readTasks(await wai(['status']));
    tasksView.set(tasks);
    await setState('ready');
  } catch (error) {
    tasks = [];
    tasksView.set([]);
    // Exit 4 here means "not initialized"; anything else (e.g. exit 3, folder inside infra) is an error.
    if (error instanceof WaiFailure && error.code === 4) {
      await setState('noProject');
    } else {
      showFailure(error);
      await setState('error');
    }
  }
}

// One refresh at a time; a request during a refresh runs once more afterwards.
async function refresh(): Promise<void> {
  if (refreshing) {
    refreshAgain = true;
    return refreshing;
  }
  refreshing = (async () => {
    do {
      refreshAgain = false;
      await doRefresh();
    } while (refreshAgain);
  })().finally(() => { refreshing = undefined; });
  return refreshing;
}

function wai(command: string[], options: string[] = [], positionals: string[] = []): Promise<Record<string, unknown>> {
  if (!cfg || !projectRoot) {
    return Promise.reject(new WaiFailure(vscode.l10n.t('wai is not available; run Workshop AI: Locate wai.')));
  }
  return runWai(cfg, projectRoot, command, options, positionals, undefined, (line) => log.info(line));
}

function taskFile(root: string, id: string): vscode.Uri {
  return vscode.Uri.file(path.join(root, '.workshop-ai', 'tasks', id, 'task.md'));
}

// Commands ---------------------------------------------------------------------------------------------------
// Commands ignore caller-supplied arguments except a validated task id (openTask) and explorer files (addContext).

async function confirmClients(): Promise<void> {
  refreshClients();
  const picks = await vscode.window.showQuickPick(
    clients.map((c) => ({
      label: CLIENT_NAMES[c.id],
      description: c.source,
      detail: c.path ? plainText(c.path, 300) : undefined,
      picked: c.confirmed || (c.source !== 'not found' && !clients.some((x) => x.confirmed)),
      id: c.id,
    })),
    { canPickMany: true, title: vscode.l10n.t('Which AI clients do you use?'), ignoreFocusOut: true },
  );
  if (!picks) {
    return;
  }
  const previous = readConfirmed(settings().inspect('clients')?.globalValue);
  const next: ConfirmedClient[] = [];
  for (const pick of picks) {
    const state = clients.find((c) => c.id === pick.id)!;
    const override = previous.find((c) => c.id === pick.id)?.path;
    if (state.source !== 'not found') {
      next.push(override ? { id: pick.id, path: override } : { id: pick.id });
      continue;
    }
    const chosen = await vscode.window.showOpenDialog({
      canSelectFiles: true, canSelectFolders: false, canSelectMany: false,
      title: vscode.l10n.t('Choose the {0} executable', CLIENT_NAMES[pick.id]),
      filters: process.platform === 'win32' ? { [vscode.l10n.t('Programs')]: ['exe', 'cmd'] } : undefined,
    });
    if (chosen?.[0]) {
      next.push({ id: pick.id, path: chosen[0].fsPath });
    }
  }
  await settings().update('clients', next, vscode.ConfigurationTarget.Global);
  refreshClients();
}

async function locateWai(): Promise<void> {
  const folder = await vscode.window.showOpenDialog({
    canSelectFiles: false, canSelectFolders: true, canSelectMany: false,
    title: vscode.l10n.t('Choose the Workshop AI product folder (it contains workshop_ai)'),
  });
  if (!folder?.[0]) {
    return;
  }
  if (!findWaiFolder(folder[0].fsPath, extensionPath)) {
    void vscode.window.showErrorMessage(vscode.l10n.t('No workshop_ai package in {0}.', folder[0].fsPath));
    return;
  }
  await settings().update('waiPath', folder[0].fsPath, vscode.ConfigurationTarget.Global);
  if (!findPython(machineSetting('pythonPath'), process.env)) {
    const python = await vscode.window.showOpenDialog({
      canSelectFiles: true, canSelectFolders: false, canSelectMany: false,
      title: vscode.l10n.t('Python was not found on PATH: choose python.exe'),
      filters: process.platform === 'win32' ? { Python: ['exe'] } : undefined,
    });
    if (python?.[0] && isFile(python[0].fsPath)) {
      await settings().update('pythonPath', python[0].fsPath, vscode.ConfigurationTarget.Global);
    }
  }
  await refresh();
}

async function initProject(): Promise<void> {
  try {
    const result = await wai(['init']);
    void vscode.window.showInformationMessage(result.created
      ? vscode.l10n.t('Workshop AI is set up in this folder (.workshop-ai/). You can delete it to undo.')
      : vscode.l10n.t('Workshop AI was already set up here; nothing changed.'));
  } catch (error) {
    showFailure(error);
  }
  await refresh();
}

async function newTask(): Promise<void> {
  if (state !== 'ready' || !projectRoot) {
    return;
  }
  const usable = clients.filter((c) => c.confirmed && c.source !== 'not found');
  if (!usable.length) {
    const action = vscode.l10n.t('Confirm AI clients');
    if (await vscode.window.showWarningMessage(vscode.l10n.t('Confirm at least one AI client first.'), action) === action) {
      await confirmClients();
    }
    return;
  }
  const id = await vscode.window.showInputBox({
    title: vscode.l10n.t('New task: id'),
    prompt: vscode.l10n.t('Lowercase letters, digits and "-", up to 64 characters (e.g. t2-empty-csv).'),
    ignoreFocusOut: true,
    validateInput: (value) => TASK_ID_RE.test(value) ? undefined
      : vscode.l10n.t('Use lowercase letters, digits and "-", starting with a letter or digit.'),
  });
  if (!id || !isTaskId(id)) {
    return;
  }
  const client = await vscode.window.showQuickPick(
    usable.map((c) => ({ label: CLIENT_NAMES[c.id], description: c.source, id: c.id as ClientId })),
    { title: vscode.l10n.t('New task {0}: which client works on it?', id), ignoreFocusOut: true },
  );
  if (!client || !CLIENT_IDS.includes(client.id)) {
    return;
  }
  const root = projectRoot;
  try {
    await wai(['task', 'new'], ['--client', client.id, '--no-edit'], [id]);
  } catch (error) {
    showFailure(error);
    return;
  }
  await refresh();
  await vscode.window.showTextDocument(taskFile(root, id));
  void vscode.window.showInformationMessage(vscode.l10n.t(
    'Task {0} created for {1}. Fill in Objective and Acceptance criteria, then save.', id, CLIENT_NAMES[client.id]));
}

async function openTask(arg: unknown): Promise<void> {
  if (!projectRoot || !isTaskId(arg) || !tasks.some((t) => t.id === arg)) {
    return;
  }
  await vscode.window.showTextDocument(taskFile(projectRoot, arg));
}

async function addContext(uri: unknown, uris: unknown): Promise<void> {
  if (state !== 'ready' || !projectRoot) {
    return;
  }
  const root = projectRoot;
  const given = (Array.isArray(uris) && uris.length ? uris : [uri ?? vscode.window.activeTextEditor?.document.uri])
    .filter((u): u is vscode.Uri => u instanceof vscode.Uri && u.scheme === 'file');
  const inside = given.map((u) => path.relative(root, u.fsPath))
    .filter((rel) => rel && !rel.startsWith('..') && !path.isAbsolute(rel));
  const files = [...new Set(inside)].filter((rel) => isFile(path.join(root, rel)));
  const skipped = given.length - files.length;
  if (!files.length) {
    void vscode.window.showWarningMessage(vscode.l10n.t('Choose one or more files inside this project folder.'));
    return;
  }
  const usable = tasks.filter((t) => !t.error);
  if (!usable.length) {
    void vscode.window.showWarningMessage(vscode.l10n.t('Create a task first.'));
    return;
  }
  const pick = await vscode.window.showQuickPick(
    usable.map((t) => ({ label: t.id, description: `${plainText(t.client, 20)} · ${plainText(t.status, 20)}` })),
    { title: vscode.l10n.t('Add {0} file(s) to which task?', files.length), ignoreFocusOut: true },
  );
  if (!pick || !isTaskId(pick.label)) {
    return;
  }
  // Another extension can invoke this command with its own file list, so the list is always shown (EXT-07 spirit).
  const shown = files.slice(0, 20).map((f) => `- ${plainText(f, 200)}`).join('\n')
    + (files.length > 20 ? `\n${vscode.l10n.t('…and {0} more', files.length - 20)}` : '');
  const add = vscode.l10n.t('Add to {0}', pick.label);
  const answer = await vscode.window.showWarningMessage(
    vscode.l10n.t('Add {0} file(s) to the context of task {1}?', files.length, pick.label),
    { modal: true, detail: shown + (skipped ? `\n${vscode.l10n.t('Skipped (folders, duplicates or outside the project): {0}', skipped)}` : '') },
    add);
  if (answer !== add) {
    return;
  }
  try {
    const result = await wai(['context', 'add'], [], [pick.label, ...files]);
    const count = Array.isArray(result.context) ? result.context.length : 0;
    void vscode.window.showInformationMessage(
      vscode.l10n.t('Task {0} now has {1} context file(s).', pick.label, count));
  } catch (error) {
    showFailure(error);
  }
}

// Activation ---------------------------------------------------------------------------------------------------

// Read-only watch of the first folder's .workshop-ai/: any change re-reads the task list through wai.
function watchProject(): void {
  watcher?.dispose();
  watcher = undefined;
  const folder = vscode.workspace.workspaceFolders?.find((f) => f.uri.scheme === 'file');
  if (!folder) {
    return;
  }
  const fsWatcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(folder, '{.workshop-ai,.workshop-ai/project-state.md,.workshop-ai/tasks/**}'));
  let timer: NodeJS.Timeout | undefined;
  const later = () => {
    clearTimeout(timer);
    timer = setTimeout(() => void refresh().catch(showFailure), 500);
  };
  watcher = vscode.Disposable.from(fsWatcher, fsWatcher.onDidCreate(later), fsWatcher.onDidChange(later),
    fsWatcher.onDidDelete(later), { dispose: () => clearTimeout(timer) });
}

export function activate(context: vscode.ExtensionContext): void {
  extensionPath = context.extensionPath;
  log = vscode.window.createOutputChannel('Workshop AI', { log: true });
  void vscode.commands.executeCommand('setContext', 'workshopAi.state', state);
  const run = (fn: (...args: unknown[]) => Promise<void>) => (...args: unknown[]) =>
    (trusted() ? fn(...args) : Promise.resolve()).catch(showFailure);
  context.subscriptions.push(
    log,
    { dispose: () => watcher?.dispose() },
    vscode.window.registerTreeDataProvider('workshopAi.clients', clientsView),
    vscode.window.registerTreeDataProvider('workshopAi.tasks', tasksView),
    vscode.commands.registerCommand('workshopAi.refresh', run(() => {
      failedConfig = ''; // a manual Refresh retries a wai check that failed before
      return refresh();
    })),
    vscode.commands.registerCommand('workshopAi.confirmClients', run(() => confirmClients())),
    vscode.commands.registerCommand('workshopAi.locateWai', run(() => locateWai())),
    vscode.commands.registerCommand('workshopAi.initProject', run(() => initProject())),
    vscode.commands.registerCommand('workshopAi.newTask', run(() => newTask())),
    vscode.commands.registerCommand('workshopAi.openTask', run((id) => openTask(id))),
    vscode.commands.registerCommand('workshopAi.addContext', run((uri, uris) => addContext(uri, uris))),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('workshopAi')) {
        void refresh().catch(showFailure);
      }
    }),
    vscode.workspace.onDidChangeWorkspaceFolders(() => {
      watchProject();
      void refresh().catch(showFailure);
    }),
  );
  watchProject();
  void refresh().catch(showFailure);
}

export function deactivate(): void {}
