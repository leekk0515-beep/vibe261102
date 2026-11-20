/** 서버와 클라이언트가 함께 쓰는 게시판 상수(카테고리, 정렬). */

export const CATEGORIES = [
  { value: "notice", label: "공지" },
  { value: "free", label: "자유" },
  { value: "question", label: "질문" },
  { value: "info", label: "정보" },
] as const;

export type Category = (typeof CATEGORIES)[number]["value"];

export const DEFAULT_CATEGORY: Category = "free";

export function isCategory(v: unknown): v is Category {
  return CATEGORIES.some((c) => c.value === v);
}

export function categoryLabel(v: string) {
  return CATEGORIES.find((c) => c.value === v)?.label ?? v;
}

export const SORTS = [
  { value: "latest", label: "최신순" },
  { value: "views", label: "조회순" },
  { value: "likes", label: "좋아요순" },
  { value: "comments", label: "댓글 많은 순" },
] as const;

export type SortKey = (typeof SORTS)[number]["value"];

export function isSortKey(v: unknown): v is SortKey {
  return SORTS.some((s) => s.value === v);
}
