import * as store from './store.js';
import { render } from './render.js';
import { MAX_LENGTH } from './utils.js';

const $ = (id) => document.getElementById(id);

const els = {
  warning: $('storage-warning'),
  today: $('today'),
  progressBar: $('progress-bar'),
  progressFill: $('progress-fill'),
  progressText: $('progress-text'),
  celebrate: $('celebrate'),
  rollover: $('rollover'),
  rolloverText: $('rollover-text'),
  rolloverAccept: $('rollover-accept'),
  rolloverDecline: $('rollover-decline'),
  form: $('add-form'),
  input: $('new-todo'),
  priority: $('new-priority'),
  charCount: $('char-count'),
  filterButtons: document.querySelectorAll('[data-filter]'),
  list: $('todo-list'),
  empty: $('empty'),
  clearCompleted: $('clear-completed'),
  themeToggle: $('theme-toggle'),
  toast: $('toast'),
  toastMsg: $('toast-msg'),
  toastUndo: $('toast-undo'),
  template: $('todo-template'),
};

const idOf = (el) => el.closest('.todo')?.dataset.id;

store.init();
store.subscribe(() => render(els));
render(els);

// ---------- 추가 ----------

function updateCharCount() {
  const length = els.input.value.length;
  els.charCount.textContent = `${length} / ${MAX_LENGTH}`;
  els.charCount.classList.toggle('limit', length >= MAX_LENGTH);
}

els.input.addEventListener('input', updateCharCount);

els.form.addEventListener('submit', (e) => {
  e.preventDefault();
  if (store.addTodo(els.input.value, els.priority.value)) {
    els.input.value = '';
    updateCharCount();
  }
  els.input.focus();
});

// ---------- 목록 (이벤트 위임) ----------

els.list.addEventListener('change', (e) => {
  if (e.target.matches('.todo-check')) store.toggleTodo(idOf(e.target));
});

els.list.addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-action]');
  if (!btn) return;
  const id = idOf(btn);
  if (btn.dataset.action === 'edit') {
    store.startEdit(id);
  } else if (btn.dataset.action === 'remove') {
    store.removeTodo(id);
    showToast('삭제했어요');
    els.input.focus();
  }
});

els.list.addEventListener('dblclick', (e) => {
  const text = e.target.closest('.todo-text');
  if (text) store.startEdit(idOf(text));
});

els.list.addEventListener('keydown', (e) => {
  if (e.target.matches('.edit-input')) {
    if (e.key === 'Enter') {
      e.preventDefault();
      store.editTodo(idOf(e.target), e.target.value);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      store.cancelEdit();
    }
    return;
  }
  if (e.altKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
    const id = idOf(e.target);
    if (!id) return;
    e.preventDefault();
    store.moveBy(id, e.key === 'ArrowUp' ? -1 : 1);
  }
});

// 편집 중 다른 곳을 누르면 저장한다
els.list.addEventListener('focusout', (e) => {
  if (!e.target.matches('.edit-input')) return;
  const id = idOf(e.target);
  if (store.getState().editingId === id) store.editTodo(id, e.target.value);
});

// ---------- 드래그 정렬 ----------

let dragId = null;

function clearDropMarkers() {
  els.list.querySelectorAll('.drop-before, .drop-after').forEach((li) => {
    li.classList.remove('drop-before', 'drop-after');
  });
}

// 손잡이를 잡았을 때만 드래그를 허용해 텍스트 선택과 충돌하지 않게 한다
els.list.addEventListener('pointerdown', (e) => {
  const handle = e.target.closest('.drag-handle');
  if (handle) handle.closest('.todo').draggable = true;
});

els.list.addEventListener('pointerup', (e) => {
  const li = e.target.closest('.todo');
  if (li && !dragId) li.draggable = false;
});

els.list.addEventListener('dragstart', (e) => {
  const li = e.target.closest('.todo');
  if (!li) return;
  dragId = li.dataset.id;
  li.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', dragId);
});

els.list.addEventListener('dragover', (e) => {
  const li = e.target.closest('.todo');
  if (!li || !dragId || !store.canMove(dragId, li.dataset.id)) return;
  e.preventDefault();
  const rect = li.getBoundingClientRect();
  const after = e.clientY > rect.top + rect.height / 2;
  clearDropMarkers();
  li.classList.add(after ? 'drop-after' : 'drop-before');
});

els.list.addEventListener('dragleave', (e) => {
  if (!els.list.contains(e.relatedTarget)) clearDropMarkers();
});

els.list.addEventListener('drop', (e) => {
  const li = e.target.closest('.todo');
  if (!li || !dragId) return;
  e.preventDefault();
  const after = li.classList.contains('drop-after');
  store.moveTodo(dragId, li.dataset.id, after);
});

els.list.addEventListener('dragend', () => {
  dragId = null;
  clearDropMarkers();
  els.list.querySelectorAll('.todo').forEach((li) => {
    li.draggable = false;
    li.classList.remove('dragging');
  });
});

// ---------- 필터 / 일괄 삭제 / 테마 ----------

els.filterButtons.forEach((btn) => {
  btn.addEventListener('click', () => store.setFilter(btn.dataset.filter));
});

els.clearCompleted.addEventListener('click', () => {
  const count = store.clearCompleted();
  if (count) showToast(`완료 항목 ${count}개를 지웠어요`);
});

els.themeToggle.addEventListener('click', () => store.cycleTheme());

// ---------- 날짜 이월 ----------

els.rolloverAccept.addEventListener('click', () => store.acceptRollover());
els.rolloverDecline.addEventListener('click', () => store.declineRollover());

// 자정을 넘겨 탭을 열어 둔 경우에도 날짜 전환을 처리한다
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) store.checkDate();
});
setInterval(() => store.checkDate(), 60_000);

// ---------- 실행 취소 토스트 ----------

let toastTimer = null;

function showToast(message) {
  els.toastMsg.textContent = message;
  els.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(hideToast, 5000);
}

function hideToast() {
  clearTimeout(toastTimer);
  els.toast.hidden = true;
  store.clearUndo();
}

els.toastUndo.addEventListener('click', () => {
  store.undoRemove();
  hideToast();
  els.input.focus();
});
