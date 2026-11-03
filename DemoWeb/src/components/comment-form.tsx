"use client";

import { useActionState, useEffect, useId, useRef } from "react";
import { Loader2Icon, SendIcon } from "lucide-react";
import { toast } from "sonner";

import { addCommentAction, type FormState } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function CommentForm({ postId }: { postId: string }) {
  const [state, formAction, pending] = useActionState<FormState, FormData>(
    addCommentAction.bind(null, postId),
    {},
  );
  const contentRef = useRef<HTMLTextAreaElement>(null);
  const errors = state.errors ?? {};
  const uid = useId();

  useEffect(() => {
    if (state.ok) {
      toast.success("댓글을 등록했습니다.");
      if (contentRef.current) contentRef.current.value = "";
    }
  }, [state]);

  return (
    <form action={formAction} noValidate className="grid gap-3">
      {state.message && (
        <p className="text-sm text-destructive" role="alert">
          {state.message}
        </p>
      )}
      <div className="grid gap-2 sm:max-w-xs">
        <Label htmlFor={`${uid}-author`}>작성자</Label>
        <Input
          id={`${uid}-author`}
          name="author"
          placeholder="이름 또는 닉네임"
          maxLength={20}
          defaultValue={state.values?.author}
          aria-invalid={!!errors.author}
        />
        {errors.author && (
          <p className="text-sm text-destructive">{errors.author}</p>
        )}
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${uid}-content`}>댓글</Label>
        <Textarea
          ref={contentRef}
          id={`${uid}-content`}
          name="content"
          placeholder="댓글을 입력하세요"
          maxLength={1000}
          defaultValue={state.ok ? "" : state.values?.content}
          aria-invalid={!!errors.content}
        />
        {errors.content && (
          <p className="text-sm text-destructive">{errors.content}</p>
        )}
      </div>
      <div className="flex justify-end">
        <Button type="submit" disabled={pending}>
          {pending ? (
            <Loader2Icon className="animate-spin" data-icon="inline-start" />
          ) : (
            <SendIcon data-icon="inline-start" />
          )}
          댓글 등록
        </Button>
      </div>
    </form>
  );
}
