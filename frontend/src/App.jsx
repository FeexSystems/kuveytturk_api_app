import { useEffect, useState, useRef } from "react";

export default function App() {
  const [accounts, setAccounts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [txs, setTxs] = useState([]);
  const pollRef = useRef(null);

  const API = import.meta.env.VITE_API_BASE || ""; // prod: same-origin, dev: set VITE_API_BASE
  const login = () => {
    window.location.href = `${API}/auth/login`;
  };

  const fetchAccounts = async () => {
    const r = await fetch(`${API}/api/accounts`);
    if (!r.ok) return alert("Auth first (Login)");
    const data = await r.json();
    setAccounts(data?.accounts || data?.data || []);
  };

  const fetchTxs = async (id) => {
    const r = await fetch(`${API}/api/accounts/${id}/transactions`);
    const data = await r.json();
    setTxs(data?.transactions || data?.data || []);
  };

  const startPolling = (id) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => fetchTxs(id), 3000);
  };

  useEffect(() => {
    return () => pollRef.current && clearInterval(pollRef.current);
  }, []);

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <h1>Kuveyt Türk – Sandbox Console</h1>
      <button onClick={login}>Login with Kuveyt Türk</button>
      <button onClick={fetchAccounts} style={{ marginLeft: 12 }}>Load Accounts</button>

      <hr />

      <h2>Accounts</h2>
      <ul>
        {accounts.map(a => (
          <li key={a.id || a.accountId}>
            <button onClick={() => { setSelected(a); fetchTxs(a.id || a.accountId); startPolling(a.id || a.accountId); }}>
              {(a.iban || a.accountNumber)} • {a.currency} • {a.balance?.available ?? a.balance}
            </button>
          </li>
        ))}
      </ul>

      {selected && (
        <>
          <h3>New Transfer</h3>
          <TransferForm accountId={selected.id || selected.accountId}
            onSubmitted={() => fetchTxs(selected.id || selected.accountId)} />
          <h3>Recent Transactions (auto-refreshing)</h3>
          <pre style={{ background: "#111", color: "#0f0", padding: 16, overflow: "auto" }}>
{JSON.stringify(txs, null, 2)}
          </pre>
        </>
      )}
    </div>
  );
}

function TransferForm({ accountId, onSubmitted }) {
  const [form, setForm] = useState({
    fromAccountId: accountId,
    toIban: "",
    amount: "",
    description: "Test payment via sandbox"
  });

  const submit = async (e) => {
    e.preventDefault();
    const r = await fetch(`${API}/api/payments/transfer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form)
    });
    const data = await r.json();
    if (!r.ok) return alert(JSON.stringify(data));
    onSubmitted?.();
  };

  return (
    <form onSubmit={submit}>
      <input placeholder="To IBAN" value={form.toIban}
             onChange={e => setForm({ ...form, toIban: e.target.value })}/>
      <input placeholder="Amount" value={form.amount}
             onChange={e => setForm({ ...form, amount: e.target.value })}/>
      <input placeholder="Description" value={form.description}
             onChange={e => setForm({ ...form, description: e.target.value })}/>
      <button type="submit">Send</button>
    </form>
  );
}
