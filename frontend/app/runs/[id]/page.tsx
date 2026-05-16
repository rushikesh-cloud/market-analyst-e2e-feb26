import { AppShell } from "@/components/app-shell";
import { RunWorkspace } from "@/components/run-workspace";

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <AppShell>
      <RunWorkspace runId={id} />
    </AppShell>
  );
}
