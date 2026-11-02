import { MAX_LENGTH, PRIORITY_RANK, todayKey, uid } from './utils.js';

const KEYS = {
  data: 'todayTodo:v1:data',
  backup: 'todayTodo:v1:data:backup',
  filter: 'todayTodo:v1:filter',
  theme: 'todayTodo:v1:theme',
};

const FILTERS = ['all', 'active', 'completed'];
const THEMES = ['system', 'light', 'dark'];

const state = {
  date: todayKey(),
  todos: [],
  filter: 'all',
  theme: 'system',
  storageOk: true,
  editingId: null,
  lastRemoved: null, // 실행 취소용으로 보관한 삭제 항목
  rollover: null,    // { from: 'YYYY-MM-DD', ids: [...] }
};

const listeners = new Set();

// ---------- 저장소 ----------

function read(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    state.storageOk = false;
    return null;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    state.storageOk = false;
  }
}

function checkStorage() {
  try {
    const probe = '__todayTodo_probe__';
    localStorage.setItem(probe, '1');
    localStorage.removeItem(probe);
    return true;
  } catch {
    return false;
  }
}

function normalize(raw) {
  if (!raw || typeof raw.text !== 'string' || !raw.text.trim()) return null;
  return {
    id: typeof raw.id === 'string' ? raw.id : uid(),
    text: raw.text.trim().slice(0, MAX_LENGTH),
    completed: Boolean(raw.completed),
    priority: raw.priority in PRIORITY_RANK ? raw.priority : 'medium',
    createdAt: typeof raw.createdAt === 'string' ? raw.createdAt : new Date().toISOString(),
    completedAt: typeof raw.completedAt === 'string' ? raw.completedAt : null,
    order: Number.isFinite(raw.order) ? raw.order : 0,
  };
}

function loadData() {
  const raw = read(KEYS.data);
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.todos)) throw new Error('invalid data');
    state.date = typeof parsed.date === 'string' ? parsed.date : todayKey();
    state.todos = parsed.todos.map(normalize).filter(Boolean);
  } catch {
    // 손상된 데이터는 지우지 않고 백업 키에 보존한다
    write(KEYS.backup, raw);
  }
}

function save() {
  write(KEYS.data, JSON.stringify({ date: state.date, todos: state.todos }));
}

function notify() {
  listeners.forEach((fn) => fn(state));
}

function commit() {
  save();
  notify();
}

// ---------- 날짜 전환 ----------

function applyDateChange() {
  const today = todayKey();
  if (state.date === today) return false;
  const from = state.date;
  // 완료 항목은 정리하고, 미완료 항목은 이월 여부를 묻는다
  state.todos = state.todos.filter((t) => !t.completed);
  state.rollover = state.todos.length ? { from, ids: state.todos.map((t) => t.id) } : null;
  state.date = today;
  state.lastRemoved = null;
  state.editingId = null;
  return true;
}

// ---------- 공개 API ----------

export function init() {
  state.storageOk = checkStorage();
  loadData();
  const filter = read(KEYS.filter);
  if (FILTERS.includes(filter)) state.filter = filter;
  const theme = read(KEYS.theme);
  if (THEMES.includes(theme)) state.theme = theme;
  if (applyDateChange()) save();
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function getState() {
  return state;
}

export function sortedTodos() {
  return [...state.todos].sort((a, b) =>
    Number(a.completed) - Number(b.completed) ||
    PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority] ||
    a.order - b.order
  );
}

export function visibleTodos() {
  const list = sortedTodos();
  if (state.filter === 'active') return list.filter((t) => !t.completed);
  if (state.filter === 'completed') return list.filter((t) => t.completed);
  return list;
}

export function counts() {
  const total = state.todos.length;
  const done = state.todos.filter((t) => t.completed).length;
  return { total, done, active: total - done };
}

export function rolloverCount() {
  if (!state.rollover) return 0;
  const ids = new Set(state.rollover.ids);
  return state.todos.filter((t) => ids.has(t.id) && !t.completed).length;
}

export function addTodo(text, priority = 'medium') {
  const value = text.trim().slice(0, MAX_LENGTH);
  if (!value) return false;
  const maxOrder = state.todos.reduce((max, t) => Math.max(max, t.order), -1);
  state.todos.push({
    id: uid(),
    text: value,
    completed: false,
    priority: priority in PRIORITY_RANK ? priority : 'medium',
    createdAt: new Date().toISOString(),
    completedAt: null,
    order: maxOrder + 1,
  });
  commit();
  return true;
}

export function toggleTodo(id) {
  const todo = state.todos.find((t) => t.id === id);
  if (!todo) return;
  todo.completed = !todo.completed;
  todo.completedAt = todo.completed ? new Date().toISOString() : null;
  commit();
}

export function startEdit(id) {
  state.editingId = id;
  notify();
}

export function cancelEdit() {
  state.editingId = null;
  notify();
}

export function editTodo(id, text) {
  const todo = state.todos.find((t) => t.id === id);
  const value = text.trim().slice(0, MAX_LENGTH);
  state.editingId = null;
  // 빈 값으로 저장하면 기존 내용을 유지한다
  if (todo && value) todo.text = value;
  commit();
}

export function removeTodo(id) {
  const todo = state.todos.find((t) => t.id === id);
  if (!todo) return;
  state.todos = state.todos.filter((t) => t.id !== id);
  state.lastRemoved = [todo];
  if (state.editingId === id) state.editingId = null;
  commit();
}

export function clearCompleted() {
  const removed = state.todos.filter((t) => t.completed);
  if (!removed.length) return 0;
  state.todos = state.todos.filter((t) => !t.completed);
  state.lastRemoved = removed;
  commit();
  return removed.length;
}

export function undoRemove() {
  if (!state.lastRemoved) return;
  state.todos.push(...state.lastRemoved);
  state.lastRemoved = null;
  commit();
}

export function clearUndo() {
  state.lastRemoved = null;
}

export function setFilter(filter) {
  if (!FILTERS.includes(filter)) return;
  state.filter = filter;
  write(KEYS.filter, filter);
  notify();
}

export function cycleTheme() {
  state.theme = THEMES[(THEMES.indexOf(state.theme) + 1) % THEMES.length];
  write(KEYS.theme, state.theme);
  notify();
}

// 같은 그룹(완료 여부 + 우선순위) 안에서만 순서를 바꿀 수 있다
export function canMove(id, targetId) {
  const a = state.todos.find((t) => t.id === id);
  const b = state.todos.find((t) => t.id === targetId);
  return Boolean(a && b && a !== b && a.completed === b.completed && a.priority === b.priority);
}

export function moveTodo(id, targetId, placeAfter) {
  if (!canMove(id, targetId)) return;
  const list = sortedTodos();
  const moving = list.find((t) => t.id === id);
  list.splice(list.indexOf(moving), 1);
  const targetIndex = list.findIndex((t) => t.id === targetId);
  list.splice(placeAfter ? targetIndex + 1 : targetIndex, 0, moving);
  list.forEach((t, i) => { t.order = i; });
  commit();
}

export function moveBy(id, delta) {
  const list = sortedTodos();
  const index = list.findIndex((t) => t.id === id);
  const neighbor = list[index + delta];
  if (index < 0 || !neighbor || !canMove(id, neighbor.id)) return;
  const current = list[index];
  [current.order, neighbor.order] = [neighbor.order, current.order];
  commit();
}

export function checkDate() {
  if (applyDateChange()) commit();
}

export function acceptRollover() {
  state.rollover = null;
  notify();
}

export function declineRollover() {
  if (!state.rollover) return;
  const ids = new Set(state.rollover.ids);
  state.todos = state.todos.filter((t) => !ids.has(t.id));
  state.rollover = null;
  commit();
}
