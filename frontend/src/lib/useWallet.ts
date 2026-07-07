import { useState, useEffect, useCallback } from "react";
import { setWalletProvider, activateDemo, activateMetaMask, resetBurner } from "./genlayer";

export function useWallet() {
  const [address, setAddress] = useState<string | null>(null);
  const [mode, setMode] = useState<"metamask" | "demo" | null>(null);
  const [mmProvider, setMmProvider] = useState<any>(null);

  useEffect(() => {
    function onAnnounce(e: any) {
      if (e.detail?.info?.rdns === "io.metamask" && e.detail?.provider) {
        setMmProvider(e.detail.provider);
      }
    }
    window.addEventListener("eip6963:announceProvider", onAnnounce as EventListener);
    window.dispatchEvent(new Event("eip6963:requestProvider"));
    return () => window.removeEventListener("eip6963:announceProvider", onAnnounce as EventListener);
  }, []);

  const connectMetaMask = useCallback(async () => {
    const provider = mmProvider ?? (window as any).ethereum;
    if (!provider) {
      alert("MetaMask not found. Use Demo mode, or install MetaMask.");
      return;
    }
    setWalletProvider(provider);
    const accounts = await provider.request({ method: "eth_requestAccounts" });
    const addr = (accounts[0] as string).toLowerCase();
    activateMetaMask(addr);
    setAddress(addr);
    setMode("metamask");
  }, [mmProvider]);

  const useDemo = useCallback(() => {
    const addr = activateDemo();
    setAddress(addr);
    setMode("demo");
  }, []);

  const newDemoWallet = useCallback(() => {
    resetBurner();
    const addr = activateDemo();
    setAddress(addr);
    setMode("demo");
  }, []);

  const disconnect = useCallback(() => {
    setAddress(null);
    setMode(null);
  }, []);

  return { address, mode, connectMetaMask, useDemo, newDemoWallet, disconnect };
}
