const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

export const MAX_LENGTH = 100;

export const PRIORITY_RANK = { high: 0, medium: 1, low: 2 };
export const PRIORITY_LABEL = { high: '높음', medium: '보통', low: '낮음' };

// 2026년 11월 2일 (월)
export function formatDate(date = new Date()) {
  return `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일 (${WEEKDAYS[date.getDay()]})`;
}

// 로컬 시간 기준 YYYY-MM-DD
export function todayKey(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

// YYYY-MM-DD → 11월 1일
export function formatDateKey(key) {
  const [, month, day] = key.split('-').map(Number);
  return `${month}월 ${day}일`;
}

export function uid() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}
