import type { AgentTraceEvent, Citation } from '@/api/types';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SourcesPanel } from '@/components/sources/SourcesPanel';
import { TracePanel } from '@/components/trace/TracePanel';

interface RightPanelProps {
  tab: string;
  onTabChange: (tab: string) => void;
  citations: Citation[];
  trace: AgentTraceEvent[];
  highlightedId: number | null;
  registerRef: (id: number, el: HTMLElement | null) => void;
}

export function RightPanel({
  tab,
  onTabChange,
  citations,
  trace,
  highlightedId,
  registerRef,
}: RightPanelProps) {
  return (
    <div className="flex h-full flex-col">
      <Tabs value={tab} onValueChange={onTabChange} className="flex h-full flex-col">
        <div className="border-b border-[var(--color-border)] p-3">
          <TabsList className="w-full">
            <TabsTrigger value="sources" className="flex-1">
              引用来源{citations.length > 0 ? ` (${citations.length})` : ''}
            </TabsTrigger>
            <TabsTrigger value="trace" className="flex-1">
              Agent Trace{trace.length > 0 ? ` (${trace.length})` : ''}
            </TabsTrigger>
          </TabsList>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <TabsContent value="sources" className="h-full">
            <SourcesPanel
              citations={citations}
              highlightedId={highlightedId}
              registerRef={registerRef}
            />
          </TabsContent>
          <TabsContent value="trace" className="h-full">
            <TracePanel trace={trace} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
