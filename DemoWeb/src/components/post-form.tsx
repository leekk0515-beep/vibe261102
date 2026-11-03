"use client";

import Link from "next/link";
import { useActionState, useId } from "react";
import { Loader2Icon } from "lucide-react";

import type { FormState } from "@/app/actions";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type Props = {
  heading: string;
  submitLabel: string;
  cancelHref: string;
  action: (prev: FormState, formData: FormData) => Promise<FormState>;
  defaultValues?: { title: string; content: string; author: string };
};

export function PostForm({
  heading,
  submitLabel,
  cancelHref,
  action,
  defaultValues,
}: Props) {
  const [state, formAction, pending] = useActionState(action, {});
  const values = { ...defaultValues, ...state.values };
  const errors = state.errors ?? {};
  // 이전 화면이 숨겨진 채 유지될 수 있어 id가 문서 안에서 겹치지 않게 합니다.
  const uid = useId();
  const id = (name: string) => `${uid}-${name}`;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{heading}</CardTitle>
      </CardHeader>
      <form action={formAction} noValidate>
        <CardContent className="grid gap-5">
          {state.message && (
            <p className="text-sm text-destructive" role="alert">
              {state.message}
            </p>
          )}
          <div className="grid gap-2">
            <Label htmlFor={id("title")}>제목</Label>
            <Input
              id={id("title")}
              name="title"
              placeholder="제목을 입력하세요"
              maxLength={100}
              defaultValue={values.title}
              aria-invalid={!!errors.title}
              aria-describedby={errors.title ? id("title-error") : undefined}
            />
            {errors.title && (
              <p id={id("title-error")} className="text-sm text-destructive">
                {errors.title}
              </p>
            )}
          </div>
          <div className="grid gap-2 sm:max-w-xs">
            <Label htmlFor={id("author")}>작성자</Label>
            <Input
              id={id("author")}
              name="author"
              placeholder="이름 또는 닉네임"
              maxLength={20}
              defaultValue={values.author}
              aria-invalid={!!errors.author}
              aria-describedby={errors.author ? id("author-error") : undefined}
            />
            {errors.author && (
              <p id={id("author-error")} className="text-sm text-destructive">
                {errors.author}
              </p>
            )}
          </div>
          <div className="grid gap-2">
            <Label htmlFor={id("content")}>내용</Label>
            <Textarea
              id={id("content")}
              name="content"
              placeholder="내용을 입력하세요"
              className="min-h-64"
              defaultValue={values.content}
              aria-invalid={!!errors.content}
              aria-describedby={errors.content ? id("content-error") : undefined}
            />
            {errors.content && (
              <p id={id("content-error")} className="text-sm text-destructive">
                {errors.content}
              </p>
            )}
          </div>
        </CardContent>
        <CardFooter className="mt-6 justify-end gap-2">
          <Button variant="outline" asChild>
            <Link href={cancelHref}>취소</Link>
          </Button>
          <Button type="submit" disabled={pending}>
            {pending && <Loader2Icon className="animate-spin" data-icon="inline-start" />}
            {submitLabel}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
