import { useEffect, useState } from "react";
import { CasaScreen } from "./components/CasaScreen.tsx";
import { HomeScreen } from "./components/HomeScreen.tsx";

function pathNow(): string {
  return window.location.pathname;
}

export function App() {
  const [path, setPath] = useState(pathNow);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const onPop = () => setPath(pathNow());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  function go(to: string) {
    if (to === path) return;
    window.history.pushState({}, "", to);
    setPath(to);
  }

  function notify(text: string) {
    setToast(text);
    window.setTimeout(() => setToast(null), 2200);
  }

  return (
    <>
      {path === "/casa" ? (
        <CasaScreen onBack={() => go("/")} onNotice={notify} />
      ) : (
        <HomeScreen onCasa={() => go("/casa")} onNotice={notify} />
      )}
      {toast ? (
        <p
          className="pointer-events-none fixed bottom-24 left-6 z-20 font-ui text-[15px] text-mist"
          role="status"
        >
          {toast}
        </p>
      ) : null}
    </>
  );
}
