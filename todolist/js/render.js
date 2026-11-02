import * as store from './store.js';
import { formatDate, formatDateKey, PRIORITY_LABEL } from './utils.js';

const EMPTY_MESSAGE = {
  all: '오늘 할 일을 추가해 보세요',
  active: '진행 중인 할일이 없어요',
  completed: '아직 완료한 할일이 없어요',
};

const THEME_LABEL = { system: '시스템', light: '라이트', dark: '다크' };

export function render(els) {
  const state = store.getState();
  const { total, done, active } = store.counts();

  // 헤더
  els.today.textContent = formatDate();
  const percent = total ? Math.round((done / total) * 100) : 0;
  els.progressFill.style.width = `${percent}%`;
  els.progressFill.classList.toggle('full', total > 0 && done === total);
  els.progressBar.setAttribute('aria-valuenow', String(percent));
  els.progressText.textContent = `${done} / ${total} 완료`;
  els.celebrate.hidden = !(total > 0 && done === total);
  els.warning.hidden = state.storageOk;

  // 날짜 이월 안내
  const rollover = store.rolloverCount();
  els.rollover.hidden = rollover === 0;
  if (rollover) {
    els.rolloverText.textContent =
      `${formatDateKey(state.rollover.from)}에 끝내지 못한 할일 ${rollover}개가 있어요. 오늘로 가져올까요?`;
  }

  // 필터
  const filterCounts = { all: total, active, completed: done };
  els.filterButtons.forEach((btn) => {
    const filter = btn.dataset.filter;
    btn.setAttribute('aria-pressed', String(filter === state.filter));
    btn.querySelector('.count').textContent = filterCounts[filter];
  });

  // 목록
  const focus = captureFocus(els.list);
  const items = store.visibleTodos();
  els.list.replaceChildren(...items.map((todo) => renderItem(els.template, todo, todo.id === state.editingId)));
  els.empty.hidden = items.length > 0;
  els.empty.textContent = EMPTY_MESSAGE[state.filter];
  els.clearCompleted.disabled = done === 0;
  restoreFocus(els.list, focus, state.editingId);

  // 테마
  if (state.theme === 'system') delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = state.theme;
  els.themeToggle.dataset.mode = state.theme;
  const themeLabel = `테마: ${THEME_LABEL[state.theme]} (눌러서 변경)`;
  els.themeToggle.setAttribute('aria-label', themeLabel);
  els.themeToggle.title = themeLabel;
}

function renderItem(template, todo, editing) {
  const li = template.content.firstElementChild.cloneNode(true);
  li.dataset.id = todo.id;
  li.classList.toggle('completed', todo.completed);

  const check = li.querySelector('.todo-check');
  check.checked = todo.completed;
  check.setAttribute('aria-label', `"${todo.text}" ${todo.completed ? '완료 취소' : '완료'}`);

  const text = li.querySelector('.todo-text');
  text.textContent = todo.text;
  if (editing) {
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'edit-input';
    input.maxLength = 100;
    input.value = todo.text;
    input.setAttribute('aria-label', '할일 수정 (Enter 저장, Esc 취소)');
    text.replaceWith(input);
  }

  const badge = li.querySelector('.badge');
  badge.textContent = PRIORITY_LABEL[todo.priority];
  badge.className = `badge badge-${todo.priority}`;

  li.querySelector('[data-action="edit"]').setAttribute('aria-label', `"${todo.text}" 수정`);
  li.querySelector('[data-action="remove"]').setAttribute('aria-label', `"${todo.text}" 삭제`);
  return li;
}

// 재렌더링 뒤에도 키보드 포커스가 같은 항목의 같은 컨트롤에 남도록 한다
function captureFocus(list) {
  const active = document.activeElement;
  if (!active || !list.contains(active)) return null;
  const li = active.closest('.todo');
  if (!li) return null;
  const action = active.classList.contains('edit-input') ? 'edit' : active.dataset.action;
  return { id: li.dataset.id, action };
}

function restoreFocus(list, focus, editingId) {
  if (editingId) {
    const input = list.querySelector('.edit-input');
    if (input) {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
      return;
    }
  }
  if (!focus?.action) return;
  const li = list.querySelector(`[data-id="${CSS.escape(focus.id)}"]`);
  li?.querySelector(`[data-action="${focus.action}"]`)?.focus();
}
