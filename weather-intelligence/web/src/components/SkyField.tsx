import type { ReactNode } from "react";
import type { SkyKind } from "../../../server/types.ts";

export function SkyField({ sky, children }: { sky: SkyKind; children: ReactNode }) {
  return (
    <div className="sky relative min-h-dvh" data-sky={sky}>
      <div className="sky-grain" aria-hidden="true" />
      <div className="relative mx-auto min-h-dvh w-full max-w-[420px] px-6 pb-[7.5rem] pt-[max(1.5rem,env(safe-area-inset-top))] lg:ml-[12vw] lg:mr-auto">
        {children}
      </div>
    </div>
  );
}
