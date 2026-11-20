"use client";

import { useEffect, useState, useSyncExternalStore, useTransition } from "react";
import { EyeIcon, HeartIcon } from "lucide-react";
import { toast } from "sonner";

import { recordViewAction, setLikeAction } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/*
 * 로그인이 없는 게시판이라 "이미 본 글", "좋아요 누른 글"은 브라우저에 기억합니다.
 * - 조회: 같은 탭 세션(sessionStorage)에서는 한 번만 셉니다.
 * - 좋아요: 이 브라우저(localStorage)에서 누른 글 목록을 기억해 다시 누르면 취소됩니다.
 * 저장소를 쓸 수 없는 환경(사생활 보호 모드 등)에서도 화면은 그대로 동작합니다.
 */

const LIKED_KEY = "demoweb:liked-posts";
const LIKED_EVENT = "demoweb:liked-change";

function readLiked(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(LIKED_KEY) ?? "[]");
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

function writeLiked(ids: string[]) {
  try {
    localStorage.setItem(LIKED_KEY, JSON.stringify(ids));
  } catch {
    // 저장할 수 없으면 이번 화면에서만 반영됩니다.
  }
  window.dispatchEvent(new Event(LIKED_EVENT));
}

function subscribeLiked(cb: () => void) {
  window.addEventListener("storage", cb);
  window.addEventListener(LIKED_EVENT, cb);
  return () => {
    window.removeEventListener("storage", cb);
    window.removeEventListener(LIKED_EVENT, cb);
  };
}

export function ViewCount({ postId, initial }: { postId: string; initial: number }) {
  const [count, setCount] = useState(initial);

  useEffect(() => {
    const key = `demoweb:viewed:${postId}`;
    try {
      if (sessionStorage.getItem(key)) return;
      // 개발 모드의 effect 두 번 실행에도 한 번만 세도록 먼저 표시합니다.
      sessionStorage.setItem(key, "1");
    } catch {
      // 저장소를 못 쓰면 그대로 셉니다.
    }
    // 정리 함수로 취소하지 않습니다. 개발 모드의 두 번째 실행은 위에서 바로 끝나므로
    // 첫 요청의 결과가 화면에 반영되어야 합니다.
    recordViewAction(postId)
      .then((n) => {
        if (n !== null) setCount(n);
      })
      .catch(() => {});
  }, [postId]);

  return (
    <span className="inline-flex items-center gap-1" title="조회수">
      <EyeIcon className="size-3.5" aria-hidden />
      <span className="sr-only">조회수</span>
      {count.toLocaleString()}
    </span>
  );
}

export function LikeButton({ postId, initial }: { postId: string; initial: number }) {
  const liked = useSyncExternalStore(
    subscribeLiked,
    () => readLiked().includes(postId),
    () => false,
  );
  const [count, setCount] = useState(initial);
  const [pending, startTransition] = useTransition();

  function toggle() {
    const next = !liked;
    const ids = readLiked().filter((id) => id !== postId);
    writeLiked(next ? [...ids, postId] : ids);
    setCount((c) => Math.max(0, c + (next ? 1 : -1)));

    startTransition(async () => {
      try {
        const n = await setLikeAction(postId, next);
        if (n !== null) setCount(n);
      } catch {
        // 실패하면 되돌립니다.
        writeLiked(next ? ids : [...ids, postId]);
        setCount((c) => Math.max(0, c + (next ? -1 : 1)));
        toast.error("좋아요를 반영하지 못했습니다. 잠시 후 다시 시도해 주세요.");
      }
    });
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={toggle}
      disabled={pending}
      aria-pressed={liked}
      aria-label={liked ? "좋아요 취소" : "좋아요"}
    >
      <HeartIcon
        data-icon="inline-start"
        className={cn(liked && "fill-rose-500 text-rose-500")}
      />
      {count.toLocaleString()}
    </Button>
  );
}
