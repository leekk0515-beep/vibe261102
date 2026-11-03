import { DatabaseIcon } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** `DATABASE_URL`이 없을 때 서버 오류 대신 보여 주는 설정 안내. */
export function DatabaseNotice() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl">
          <DatabaseIcon className="size-5" />
          데이터베이스가 연결되지 않았습니다
        </CardTitle>
        <CardDescription>
          게시판을 사용하려면 Neon(PostgreSQL) 연결 문자열을 환경 변수{" "}
          <code className="rounded bg-muted px-1 py-0.5 font-mono text-foreground">
            DATABASE_URL
          </code>
          로 설정해야 합니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 text-sm">
        <section className="grid gap-1">
          <h2 className="font-medium">Vercel에 배포한 경우</h2>
          <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
            <li>
              프로젝트 <b className="text-foreground">Settings → Environment Variables</b>에서{" "}
              <code className="font-mono">DATABASE_URL</code>을 추가합니다.
            </li>
            <li>
              <b className="text-foreground">Deployments</b>에서 최근 배포를{" "}
              <b className="text-foreground">Redeploy</b>해야 반영됩니다.
            </li>
          </ol>
        </section>
        <section className="grid gap-1">
          <h2 className="font-medium">로컬에서 실행하는 경우</h2>
          <p className="text-muted-foreground">
            <code className="font-mono">.env.example</code>을{" "}
            <code className="font-mono">.env.local</code>로 복사해 값을 채운 뒤 서버를 다시
            시작합니다.
          </p>
        </section>
      </CardContent>
    </Card>
  );
}
