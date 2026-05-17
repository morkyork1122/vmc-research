import { useState, useRef } from "react";

const API_BASE = "/api";

const ASSETS     = ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT","DOGE/USDT","AVAX/USDT","MATIC/USDT"];
const TIMEFRAMES = ["15m","1H","4H","1D","1W"];

const SIGNAL_TYPES = [
  { key:"green_dot",       label:"Green Dot",   color:"#00ff88", desc:"WT1 crosses WT2 up at oversold" },
  { key:"red_dot",         label:"Red Dot",     color:"#ff3355", desc:"WT1 crosses WT2 down at overbought" },
  { key:"gold_dot",        label:"Gold Dot",    color:"#ffd700", desc:"Strong buy — WT cross below -80" },
  { key:"bull_div",        label:"Bull Div",    color:"#00ccff", desc:"Price lower low, WT higher low" },
  { key:"bear_div",        label:"Bear Div",    color:"#ff6633", desc:"Price higher high, WT lower high" },
  { key:"bull_div_hidden", label:"Bull Hidden", color:"#66ffcc", desc:"Hidden bullish divergence" },
  { key:"bear_div_hidden", label:"Bear Hidden", color:"#ff9966", desc:"Hidden bearish divergence" },
];

const HTF_MAP = {
  "1m":["15m","1H"], "5m":["1H","4H"], "15m":["1H","4H"],
  "30m":["4H","1D"], "1H":["4H","1D"], "4H":["1D","1W"],
  "1D":["1W"], "1W":[],
};

const LOADING_STEPS = [
  "Connecting to HTX","Fetching OHLCV candles","Computing WaveTrend",
  "Detecting divergences","Computing money flow","Running backtest",
  "Sending data to Claude","Generating AI report",
];

const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Bebas+Neue&family=Inter:wght@300;400;500;600&display=swap');
  *{box-sizing:border-box;margin:0;padding:0}
  :root{
    --bg:#06060e;--surface:#0c0c18;--card:#10101f;--card2:#14142a;
    --border:#1e1e38;--green:#00ff88;--red:#ff3355;--gold:#ffd700;
    --blue:#00ccff;--purple:#9966ff;--orange:#ff6633;
    --text:#d4d4f0;--muted:#5a5a8a;
    --mono:'Space Mono',monospace;--sans:'Inter',sans-serif;--display:'Bebas Neue',sans-serif;
  }
  body{background:var(--bg);color:var(--text);font-family:var(--sans)}
  .app{min-height:100vh;background:var(--bg);
    background-image:radial-gradient(ellipse at 20% 0%,rgba(0,255,136,0.04) 0%,transparent 60%),
      radial-gradient(ellipse at 80% 100%,rgba(153,102,255,0.04) 0%,transparent 60%)}
  .header{border-bottom:1px solid var(--border);padding:14px 24px;display:flex;
    align-items:center;gap:16px;background:rgba(12,12,24,0.95);
    backdrop-filter:blur(10px);position:sticky;top:0;z-index:10;flex-wrap:wrap}
  .logo{font-family:var(--display);font-size:22px;letter-spacing:2px;color:var(--green);white-space:nowrap}
  .logo span{color:var(--muted)}
  .hd{width:1px;height:28px;background:var(--border)}
  .tag{font-family:var(--mono);font-size:10px;padding:3px 8px;border-radius:3px;
    border:1px solid var(--green);color:var(--green);text-transform:uppercase;letter-spacing:1px}
  .controls{padding:16px 24px;display:flex;gap:12px;align-items:flex-end;
    flex-wrap:wrap;background:var(--surface);border-bottom:1px solid var(--border)}
  .cg{display:flex;flex-direction:column;gap:6px}
  .cl{font-family:var(--mono);font-size:9px;text-transform:uppercase;letter-spacing:2px;color:var(--muted)}
  .sw{position:relative}
  select{background:var(--card);border:1px solid var(--border);color:var(--text);
    font-family:var(--mono);font-size:13px;padding:8px 36px 8px 12px;
    border-radius:6px;cursor:pointer;appearance:none;outline:none;transition:border-color 0.2s;min-width:120px}
  select:hover,select:focus{border-color:var(--green)}
  .sa{position:absolute;right:10px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none;font-size:10px}
  .chips{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
  .chip{display:flex;align-items:center;gap:5px;padding:5px 9px;border-radius:5px;
    background:var(--card);border:1px solid var(--border);cursor:pointer;
    font-family:var(--mono);font-size:10px;transition:all 0.15s;user-select:none}
  .chip.on{border-color:currentColor;background:rgba(0,0,0,0.3)}
  .chip .dot{width:6px;height:6px;border-radius:50%}
  .btn{padding:9px 20px;border:none;border-radius:6px;font-family:var(--mono);font-size:12px;
    font-weight:700;letter-spacing:1px;text-transform:uppercase;cursor:pointer;transition:all 0.2s;
    white-space:nowrap;align-self:flex-end}
  .btn-green{background:var(--green);color:#000}
  .btn-green:hover{background:#00e87a;transform:translateY(-1px)}
  .btn-blue{background:transparent;color:var(--blue);border:1px solid var(--blue)}
  .btn-blue:hover{background:rgba(0,204,255,0.08)}
  .btn-purple{background:transparent;color:var(--purple);border:1px solid var(--purple)}
  .btn-purple:hover{background:rgba(153,102,255,0.08)}
  .btn-gold{background:transparent;color:var(--gold);border:1px solid var(--gold)}
  .btn-gold:hover{background:rgba(255,215,0,0.08)}
  .btn:disabled{opacity:0.4;cursor:not-allowed;transform:none}
  .main{padding:20px 24px;max-width:1200px;margin:0 auto}
  .legend-row{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin-bottom:20px}
  @media(max-width:900px){.legend-row{grid-template-columns:repeat(3,1fr)}}
  .lc{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px;position:relative;overflow:hidden}
  .lc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent,var(--green))}
  .lt{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--accent,var(--green));margin-bottom:3px}
  .ld{font-size:10px;color:var(--muted);line-height:1.4}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
  @media(max-width:700px){.grid2{grid-template-columns:1fr}}
  .fw{grid-column:1/-1}
  .card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px}
  .card-h{display:flex;align-items:center;gap:10px;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid var(--border)}
  .card-icon{width:26px;height:26px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0}
  .card-title{font-family:var(--mono);font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--muted)}
  .card-body{font-size:13px;line-height:1.7;color:var(--text)}
  .card-body p{margin-bottom:8px}
  .sg{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
  .si{background:var(--card2);border-radius:6px;padding:10px 12px}
  .sl{font-family:var(--mono);font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:4px}
  .sv{font-family:var(--mono);font-size:18px;font-weight:700}
  .rl{list-style:none}
  .ri{display:flex;gap:10px;padding:7px 0;border-bottom:1px solid var(--border);font-size:12px;line-height:1.5}
  .ri:last-child{border-bottom:none}
  .rn{font-family:var(--mono);font-size:9px;color:var(--green);background:rgba(0,255,136,0.08);
    border:1px solid rgba(0,255,136,0.2);border-radius:4px;padding:1px 6px;height:fit-content;margin-top:2px;flex-shrink:0}
  .wb{display:inline-flex;align-items:center;gap:5px;background:rgba(255,51,85,0.08);
    border:1px solid rgba(255,51,85,0.25);border-radius:4px;padding:2px 8px;
    font-family:var(--mono);font-size:10px;color:var(--red);margin-bottom:10px}
  .ob{display:inline-flex;align-items:center;gap:5px;background:rgba(0,255,136,0.08);
    border:1px solid rgba(0,255,136,0.25);border-radius:4px;padding:2px 8px;
    font-family:var(--mono);font-size:10px;color:var(--green);margin-bottom:10px}
  .lw{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 24px;gap:20px}
  .loader{width:44px;height:44px;border:2px solid var(--border);border-top-color:var(--green);
    border-radius:50%;animation:spin 0.8s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  .lsteps{display:flex;flex-direction:column;gap:7px}
  .lstep{font-family:var(--mono);font-size:11px;color:var(--muted);display:flex;align-items:center;gap:8px;transition:color 0.3s}
  .lstep.done{color:var(--green)}.lstep.act{color:var(--text)}
  .lstep .sd{width:6px;height:6px;border-radius:50%;background:currentColor;flex-shrink:0}
  .es{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 24px;gap:14px;text-align:center}
  .ei{font-size:48px;opacity:0.3}
  .et{font-family:var(--display);font-size:26px;letter-spacing:3px;color:var(--muted)}
  .esb{font-size:12px;color:var(--muted);max-width:420px;line-height:1.6}
  .err{background:rgba(255,51,85,0.05);border:1px solid rgba(255,51,85,0.2);border-radius:8px;
    padding:20px;font-family:var(--mono);font-size:12px;color:var(--red);text-align:center}
  h4{font-size:12px;font-weight:600;margin-bottom:7px;color:var(--text)}
  .tt{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:11px}
  .tt th{text-align:left;padding:6px 10px;color:var(--muted);border-bottom:1px solid var(--border);
    font-size:9px;text-transform:uppercase;letter-spacing:1px}
  .tt td{padding:7px 10px;border-bottom:1px solid var(--border)}
  .tt tr:last-child td{border-bottom:none}
  .bw{padding:2px 7px;border-radius:3px;font-size:10px;font-weight:700}
  .bw-w{background:rgba(0,255,136,0.15);color:var(--green)}
  .bw-l{background:rgba(255,51,85,0.12);color:var(--red)}
  .sl2{font-family:var(--mono);font-size:9px;text-transform:uppercase;letter-spacing:3px;color:var(--muted);margin-bottom:12px;padding-left:2px}
  .bsg{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;margin-top:8px}
  .bsc{background:var(--card2);border-radius:6px;padding:10px}
  .bsn{font-family:var(--mono);font-size:9px;color:var(--muted);text-transform:uppercase;margin-bottom:6px}
  .bsr{font-family:var(--mono);font-size:16px;font-weight:700}
  .bsm{font-family:var(--mono);font-size:9px;color:var(--muted);margin-top:2px}
  .mt{display:flex;gap:0;margin-left:auto}
  .mb{padding:5px 12px;font-family:var(--mono);font-size:10px;cursor:pointer;
    border:1px solid var(--border);background:transparent;color:var(--muted);transition:all 0.15s}
  .mb:first-child{border-radius:4px 0 0 4px}.mb:last-child{border-radius:0 4px 4px 0}
  .mb.on{background:var(--card2);color:var(--green);border-color:var(--green)}
  .tick{font-family:var(--mono);font-size:11px;color:var(--muted);padding:5px 24px;
    background:var(--surface);border-bottom:1px solid var(--border);display:flex;gap:24px;overflow:hidden}
  .ti{display:flex;gap:6px}

  /* Money Flow */
  .mf-bar{height:6px;border-radius:3px;background:var(--border);overflow:hidden;margin:8px 0}
  .mf-fill{height:100%;border-radius:3px;transition:width 0.5s}
  .mf-g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px}
  .mf-gauge{background:var(--card2);border-radius:8px;padding:12px;text-align:center}
  .mf-gl{font-family:var(--mono);font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:6px}
  .mf-gv{font-family:var(--mono);font-size:20px;font-weight:700}
  .mf-gs{font-size:10px;color:var(--muted);margin-top:3px}
  .mf-rs{display:flex;flex-direction:column;gap:6px;margin-top:12px}
  .mf-r{font-size:12px;padding:6px 10px;background:var(--card2);border-radius:5px;line-height:1.4}
  .bias-badge{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;border-radius:20px;
    font-family:var(--mono);font-size:12px;font-weight:700;letter-spacing:1px;margin-bottom:14px}
  .str-badge{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:4px;
    font-family:var(--mono);font-size:11px;font-weight:700;margin-left:8px}
  .obv-row{display:flex;align-items:center;gap:10px;padding:8px 12px;background:var(--card2);border-radius:6px;margin-bottom:8px}
  .obv-lbl{font-family:var(--mono);font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;min-width:80px}
  .obv-wrap{flex:1;height:4px;background:var(--border);border-radius:2px;overflow:hidden}
  .obv-fill{height:100%;border-radius:2px}
  .obv-val{font-family:var(--mono);font-size:11px;min-width:60px;text-align:right}

  /* MTF */
  .mtf-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-top:14px}
  .mtf-card{background:var(--card2);border-radius:8px;padding:14px;border:1px solid var(--border);position:relative;overflow:hidden}
  .mtf-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--mtf-color,var(--muted))}
  .mtf-tf{font-family:var(--mono);font-size:9px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:8px}
  .mtf-bias{font-family:var(--mono);font-size:20px;font-weight:700;margin-bottom:4px}
  .mtf-score{font-family:var(--mono);font-size:11px;color:var(--muted);margin-bottom:10px}
  .mtf-reasons{display:flex;flex-direction:column;gap:4px}
  .mtf-reason{font-size:11px;color:var(--muted);line-height:1.4}
  .confirm-banner{padding:14px 18px;border-radius:8px;margin-bottom:14px;display:flex;align-items:center;gap:12px}
  .confirm-icon{font-size:24px}
  .confirm-text{flex:1}
  .confirm-label{font-family:var(--mono);font-size:13px;font-weight:700;letter-spacing:1px;margin-bottom:4px}
  .confirm-summary{font-size:12px;opacity:0.8;line-height:1.5}
  .htf-hint{font-family:var(--mono);font-size:10px;color:var(--muted);padding:8px 12px;
    background:var(--card2);border-radius:6px;margin-bottom:14px}
`;

function LoadingView({ step }) {
  return (
    <div className="lw">
      <div className="loader" />
      <div className="lsteps">
        {LOADING_STEPS.map((s, i) => (
          <div key={i} className={`lstep ${i < step ? "done" : i === step ? "act" : ""}`}>
            <span className="sd" />{i < step ? "✓ " : i === step ? "▶ " : "○ "}{s}
          </div>
        ))}
      </div>
    </div>
  );
}

function Card({ icon, bg, title, children, full }) {
  return (
    <div className={`card${full ? " fw" : ""}`}>
      <div className="card-h">
        <div className="card-icon" style={{ background: bg }}>{icon}</div>
        <div className="card-title">{title}</div>
      </div>
      <div className="card-body">{children}</div>
    </div>
  );
}

function BySignal({ bySignal }) {
  if (!bySignal || !Object.keys(bySignal).length) return null;
  return (
    <div className="bsg">
      {Object.entries(bySignal).map(([sig, d]) => {
        const si  = SIGNAL_TYPES.find(s => s.key === sig);
        const wr  = d.win_rate;
        const clr = wr >= 55 ? "var(--green)" : wr >= 45 ? "var(--gold)" : "var(--red)";
        return (
          <div key={sig} className="bsc">
            <div className="bsn">{si?.label || sig}</div>
            <div className="bsr" style={{ color: clr }}>{wr}%</div>
            <div className="bsm">{d.total} trades · avg {d.avg_pnl > 0 ? "+" : ""}{d.avg_pnl}%</div>
          </div>
        );
      })}
    </div>
  );
}

function TradesTable({ trades }) {
  if (!trades?.length) return <p style={{ color:"var(--muted)",fontSize:12 }}>No trades.</p>;
  return (
    <div style={{ overflowX:"auto" }}>
      <table className="tt">
        <thead><tr>
          <th>Signal</th><th>Dir</th><th>Entry</th><th>Exit</th>
          <th>SL</th><th>TP</th><th>WT2</th><th>PnL</th><th>Result</th>
        </tr></thead>
        <tbody>
          {trades.map((t, i) => {
            const si = SIGNAL_TYPES.find(s => s.key === t.signal_type);
            return (
              <tr key={i}>
                <td style={{ color: si?.color||"var(--text)" }}>{si?.label||t.signal_type}</td>
                <td style={{ color: t.direction==="long"?"var(--green)":"var(--red)" }}>
                  {t.direction==="long"?"▲":"▼"} {t.direction}
                </td>
                <td>{t.entry_price}</td><td>{t.exit_price}</td>
                <td style={{ color:"var(--red)" }}>{t.stop_loss}</td>
                <td style={{ color:"var(--green)" }}>{t.take_profit}</td>
                <td style={{ color: t.wt2_at_entry<-53?"var(--green)":t.wt2_at_entry>53?"var(--red)":"var(--text)" }}>
                  {t.wt2_at_entry}
                </td>
                <td style={{ color: t.pnl_pct>=0?"var(--green)":"var(--red)" }}>
                  {t.pnl_pct>=0?"+":""}{t.pnl_pct}%
                </td>
                <td><span className={`bw ${t.result==="win"?"bw-w":"bw-l"}`}>{t.result}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function MoneyFlowPanel({ mf }) {
  if (!mf) return <p style={{ color:"var(--muted)",fontSize:12,textAlign:"center",padding:20 }}>Click 💰 Money Flow to analyse.</p>;
  if (mf.error) return <div className="err">⚠ {mf.error}</div>;

  const biasClr = mf.mf_bias==="BULLISH"?"var(--green)":mf.mf_bias==="BEARISH"?"var(--red)":"var(--muted)";
  const strClr  = mf.strength==="STRONG"?"var(--green)":mf.strength==="MODERATE"?"var(--gold)":"var(--red)";
  const cmfPct  = Math.min(100,Math.abs((mf.cmf||0)*500));
  const cmfClr  = (mf.cmf||0)>0?"var(--green)":"var(--red)";
  const mfiPct  = mf.mfi||50;
  const mfiClr  = mfiPct<30?"var(--green)":mfiPct>70?"var(--red)":"var(--gold)";
  const volPct  = Math.min(100,((mf.vol_ratio||1)/4)*100);
  const volClr  = mf.vol_spike?"var(--gold)":"var(--blue)";

  return (
    <div>
      <div style={{ display:"flex",alignItems:"center",marginBottom:14,flexWrap:"wrap",gap:8 }}>
        <div className="bias-badge" style={{ background:`${biasClr}15`,border:`1px solid ${biasClr}40`,color:biasClr }}>
          {mf.mf_bias==="BULLISH"?"▲":mf.mf_bias==="BEARISH"?"▼":"━"} {mf.mf_bias} FLOW
        </div>
        <div className="str-badge" style={{ background:`${strClr}15`,border:`1px solid ${strClr}40`,color:strClr }}>
          ◆ {mf.strength}
        </div>
        <div style={{ fontFamily:"var(--mono)",fontSize:10,color:"var(--muted)",marginLeft:"auto" }}>
          {mf.confluence||0}/5 confirming
        </div>
      </div>
      <div style={{ marginBottom:16 }}>
        <div style={{ display:"flex",justifyContent:"space-between",marginBottom:4 }}>
          <span style={{ fontFamily:"var(--mono)",fontSize:9,color:"var(--muted)",textTransform:"uppercase",letterSpacing:1 }}>Confidence Score</span>
          <span style={{ fontFamily:"var(--mono)",fontSize:12,color:strClr,fontWeight:700 }}>{mf.score}/100</span>
        </div>
        <div className="mf-bar"><div className="mf-fill" style={{ width:`${mf.score||50}%`,background:strClr }} /></div>
      </div>
      <div className="mf-g3">
        <div className="mf-gauge">
          <div className="mf-gl">CMF</div>
          <div className="mf-gv" style={{ color:cmfClr }}>{(mf.cmf||0)>0?"+":""}{(mf.cmf||0).toFixed(3)}</div>
          <div className="mf-gs">{(mf.cmf||0)>0.1?"Inst. Buying":(mf.cmf||0)<-0.1?"Inst. Selling":"Neutral"}</div>
        </div>
        <div className="mf-gauge">
          <div className="mf-gl">MFI</div>
          <div className="mf-gv" style={{ color:mfiClr }}>{(mf.mfi||50).toFixed(0)}</div>
          <div className="mf-gs">{mfiPct<30?"Oversold":mfiPct>70?"Overbought":"Neutral"}</div>
        </div>
        <div className="mf-gauge">
          <div className="mf-gl">Volume</div>
          <div className="mf-gv" style={{ color:volClr }}>{(mf.vol_ratio||1).toFixed(1)}x</div>
          <div className="mf-gs">{mf.vol_spike?"🔥 Spike!":"Normal"}</div>
        </div>
      </div>
      {[["CMF",cmfPct,cmfClr,`${(mf.cmf||0)>0?"+":""}${(mf.cmf||0).toFixed(3)}`],
        ["MFI",mfiPct,mfiClr,`${(mf.mfi||50).toFixed(0)}`],
        ["OBV",mf.obv_trend?.includes("Rising")?70:30,mf.obv_trend?.includes("Rising")?"var(--green)":"var(--red)",mf.obv_trend||"—"],
        ["Volume",volPct,volClr,`${(mf.vol_ratio||1).toFixed(1)}x avg`],
      ].map(([label,pct,color,val]) => (
        <div key={label} className="obv-row">
          <span className="obv-lbl">{label}</span>
          <div className="obv-wrap"><div className="obv-fill" style={{ width:`${pct}%`,background:color }} /></div>
          <span className="obv-val" style={{ color }}>{val}</span>
        </div>
      ))}
      {mf.reasons?.length > 0 && (
        <><h4 style={{ marginTop:14 }}>Analysis</h4>
        <div className="mf-rs">{mf.reasons.map((r,i) => <div key={i} className="mf-r">{r}</div>)}</div></>
      )}
    </div>
  );
}

function MTFPanel({ mtf, timeframe, signal }) {
  if (!mtf) return (
    <p style={{ color:"var(--muted)",fontSize:12,textAlign:"center",padding:20 }}>
      Click 🕐 MTF to run multi-timeframe confirmation.
    </p>
  );
  if (mtf.error) return <div className="err">⚠ {mtf.error}</div>;

  const htfs = HTF_MAP[timeframe] || [];
  const confirmColor = {
    STRONG:  "var(--green)", PARTIAL: "var(--gold)",
    NEUTRAL: "var(--muted)", AGAINST: "var(--red)",
  }[mtf.confirmation] || "var(--muted)";

  const confirmIcon = {
    STRONG:"✅✅", PARTIAL:"✅", NEUTRAL:"➖", AGAINST:"❌",
  }[mtf.confirmation] || "➖";

  return (
    <div>
      {/* HTF hint */}
      <div className="htf-hint">
        Checking {timeframe} signal against: {htfs.length ? htfs.join(" + ") : "no higher timeframes"}
      </div>

      {/* Confirmation banner */}
      <div className="confirm-banner" style={{
        background:`${confirmColor}10`,
        border:`1px solid ${confirmColor}30`,
      }}>
        <div className="confirm-icon">{confirmIcon}</div>
        <div className="confirm-text">
          <div className="confirm-label" style={{ color:confirmColor }}>
            {mtf.confirmation} CONFIRMATION
          </div>
          <div className="confirm-summary">{mtf.summary}</div>
        </div>
        <div style={{ fontFamily:"var(--mono)",fontSize:20,fontWeight:700,color:confirmColor }}>
          {mtf.overall_score}/100
        </div>
      </div>

      {/* Per-timeframe cards */}
      {mtf.timeframes && Object.keys(mtf.timeframes).length > 0 && (
        <>
          <h4>Higher Timeframe Breakdown</h4>
          <div className="mtf-grid">
            {Object.entries(mtf.timeframes).map(([tf, data]) => {
              const biasClr = data.bias==="BULLISH"?"var(--green)":data.bias==="BEARISH"?"var(--red)":"var(--muted)";
              const scoreW  = `${data.score||50}%`;
              return (
                <div key={tf} className="mtf-card" style={{ "--mtf-color": biasClr }}>
                  <div className="mtf-tf">{data.timeframe_label || tf}</div>
                  <div className="mtf-bias" style={{ color:biasClr }}>
                    {data.bias==="BULLISH"?"▲":data.bias==="BEARISH"?"▼":"━"} {data.bias}
                  </div>
                  <div className="mtf-score">{data.score}/100 confidence</div>
                  <div className="mf-bar"><div className="mf-fill" style={{ width:scoreW,background:biasClr }} /></div>
                  {/* Indicator values */}
                  {data.details && (
                    <div style={{ fontFamily:"var(--mono)",fontSize:10,color:"var(--muted)",marginTop:8,lineHeight:1.8 }}>
                      {data.details.wt1 !== undefined && <div>WT1: <span style={{ color:data.details.wt1>0?"var(--green)":"var(--red)" }}>{data.details.wt1}</span></div>}
                      {data.details.cmf !== undefined && <div>CMF: <span style={{ color:data.details.cmf>0?"var(--green)":"var(--red)" }}>{data.details.cmf > 0 ? "+" : ""}{data.details.cmf}</span></div>}
                      {data.details.mfi !== undefined && <div>MFI: <span style={{ color:data.details.mfi<30?"var(--green)":data.details.mfi>70?"var(--red)":"var(--gold)" }}>{data.details.mfi}</span></div>}
                      {data.details.obv && <div>OBV: <span style={{ color:data.details.obv.includes("Rising")?"var(--green)":"var(--red)" }}>{data.details.obv}</span></div>}
                    </div>
                  )}
                  <div className="mtf-reasons" style={{ marginTop:8 }}>
                    {(data.reasons||[]).slice(0,3).map((r,i) => <div key={i} className="mtf-reason">{r}</div>)}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* No higher TF */}
      {(!mtf.timeframes || Object.keys(mtf.timeframes).length === 0) && (
        <div style={{ textAlign:"center",color:"var(--muted)",fontSize:12,padding:20 }}>
          {timeframe} is the highest timeframe — signal taken without HTF filter.
        </div>
      )}
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function VMCResearch() {
  const [asset, setAsset]               = useState("BTC/USDT");
  const [timeframe, setTimeframe]       = useState("4H");
  const [selSigs, setSelSigs]           = useState(["green_dot","red_dot","gold_dot","bull_div","bear_div"]);
  const [loading, setLoading]           = useState(false);
  const [loadStep, setLoadStep]         = useState(0);
  const [result, setResult]             = useState(null);
  const [error, setError]               = useState(null);
  const [activeTab, setActiveTab]       = useState("report");
  const [moneyFlow, setMoneyFlow]       = useState(null);
  const [mfLoading, setMfLoading]       = useState(false);
  const [mtfData, setMtfData]           = useState(null);
  const [mtfLoading, setMtfLoading]     = useState(false);
  const [activeSig, setActiveSig]       = useState("green_dot");
  const stepRef = useRef(0);

  const toggleSig = k => setSelSigs(p => p.includes(k) ? p.filter(x=>x!==k) : [...p,k]);

  const runPipeline = async (mode="full") => {
    setLoading(true); setError(null); setResult(null);
    setMoneyFlow(null); setMtfData(null);
    stepRef.current = 0; setLoadStep(0);
    const total = mode==="full" ? LOADING_STEPS.length : 6;
    const t = setInterval(() => { stepRef.current=Math.min(stepRef.current+1,total-1); setLoadStep(stepRef.current); }, mode==="full"?2000:1200);
    try {
      const resp = await fetch(`${API_BASE}/${mode==="full"?"research":"backtest"}`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ symbol:asset, timeframe, signals:selSigs }),
      });
      if (!resp.ok) { const e=await resp.json().catch(()=>({})); throw new Error(e.detail||`Error ${resp.status}`); }
      clearInterval(t); setLoadStep(total-1);
      const data = await resp.json();
      setResult({ symbol:data.symbol, timeframe:data.timeframe, candles_used:data.candles_used,
        backtest_stats:data.backtest_stats||data.summary, recent_trades:data.recent_trades,
        ai_report:data.ai_report||null, latest_signals:data.latest_signals, mode });
      setActiveTab(mode==="full"?"report":"trades");
    } catch(err) { clearInterval(t); setError(err.message); }
    finally { setLoading(false); }
  };

  const runMoneyFlow = async () => {
    setMfLoading(true); setMoneyFlow(null);
    try {
      const resp = await fetch(`${API_BASE}/money-flow?symbol=${encodeURIComponent(asset)}&timeframe=${timeframe}&signal=${activeSig}`);
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      setMoneyFlow(await resp.json()); setActiveTab("moneyflow");
    } catch(err) { setMoneyFlow({ error:err.message }); }
    finally { setMfLoading(false); }
  };

  const runMTF = async () => {
    setMtfLoading(true); setMtfData(null);
    try {
      const resp = await fetch(`${API_BASE}/mtf?symbol=${encodeURIComponent(asset)}&timeframe=${timeframe}&signal=${activeSig}`);
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      setMtfData(await resp.json()); setActiveTab("mtf");
    } catch(err) { setMtfData({ error:err.message }); }
    finally { setMtfLoading(false); }
  };

  const busy = loading || mfLoading || mtfLoading;
  const r = result; const ai = r?.ai_report; const bt = r?.backtest_stats;
  const htfs = HTF_MAP[timeframe] || [];

  return (
    <>
      <style>{STYLES}</style>
      <div className="app">
        <div className="header">
          <div className="logo">VMC<span>_</span>RESEARCH</div>
          <div className="hd" />
          <div className="tag">Real Data</div>
          <div className="tag" style={{ borderColor:"var(--purple)",color:"var(--purple)" }}>Cipher B</div>
          <div className="tag" style={{ borderColor:"var(--gold)",color:"var(--gold)" }}>AI</div>
          <div className="tag" style={{ borderColor:"var(--blue)",color:"var(--blue)" }}>Money Flow</div>
          <div className="tag" style={{ borderColor:"var(--orange)",color:"var(--orange)" }}>MTF</div>
        </div>

        <div className="tick">
          {[["BTC","var(--green)","↑"],["ETH","var(--green)","↑"],["SOL","var(--red)","↓"],
            ["BNB","var(--green)","↑"],["DOGE","var(--red)","↓"],["AVAX","var(--green)","↑"]].map(([s,c,a]) => (
            <div key={s} className="ti"><span>{s}/USDT</span><span style={{ color:c }}>{a}</span></div>
          ))}
        </div>

        <div className="controls">
          <div className="cg">
            <div className="cl">Asset Pair</div>
            <div className="sw">
              <select value={asset} onChange={e=>setAsset(e.target.value)}>
                {ASSETS.map(a=><option key={a}>{a}</option>)}
              </select><span className="sa">▾</span>
            </div>
          </div>
          <div className="cg">
            <div className="cl">Timeframe</div>
            <div className="sw">
              <select value={timeframe} onChange={e=>setTimeframe(e.target.value)}>
                {TIMEFRAMES.map(t=><option key={t}>{t}</option>)}
              </select><span className="sa">▾</span>
            </div>
          </div>
          <div className="cg">
            <div className="cl">Signal Focus</div>
            <div className="chips">
              {SIGNAL_TYPES.map(s=>(
                <div key={s.key} className={`chip ${selSigs.includes(s.key)?"on":""}`}
                  style={{ color:selSigs.includes(s.key)?s.color:"var(--muted)" }}
                  onClick={()=>{ toggleSig(s.key); setActiveSig(s.key); }}>
                  <div className="dot" style={{ background:s.color }} />{s.label}
                </div>
              ))}
            </div>
          </div>
          <div className="cg">
            <div className="cl">MTF Signal</div>
            <div className="sw">
              <select value={activeSig} onChange={e=>setActiveSig(e.target.value)}>
                {SIGNAL_TYPES.map(s=><option key={s.key} value={s.key}>{s.label}</option>)}
              </select><span className="sa">▾</span>
            </div>
          </div>
          <button className="btn btn-green" onClick={()=>runPipeline("full")} disabled={busy}>
            {loading?"Running...":"▶ Full Research"}
          </button>
          <button className="btn btn-blue" onClick={()=>runPipeline("backtest")} disabled={busy}>⚡ Backtest</button>
          <button className="btn btn-purple" onClick={runMoneyFlow} disabled={busy}>
            {mfLoading?"Loading...":"💰 Money Flow"}
          </button>
          <button className="btn btn-gold" onClick={runMTF} disabled={busy}>
            {mtfLoading?"Loading...":"🕐 MTF"}
          </button>
        </div>

        <div className="main">
          <div className="sl2">Signal Reference</div>
          <div className="legend-row">
            {SIGNAL_TYPES.map(s=>(
              <div key={s.key} className="lc" style={{ "--accent":s.color }}>
                <div className="lt">{s.label}</div><div className="ld">{s.desc}</div>
              </div>
            ))}
          </div>

          {loading && <LoadingView step={loadStep} />}

          {error && !loading && (
            <div className="err">⚠ {error}
              <div style={{ marginTop:10,fontSize:11,color:"var(--muted)" }}>
                Make sure backend is running: <code style={{ color:"var(--blue)" }}>python main.py</code>
              </div>
            </div>
          )}

          {!loading && !r && !moneyFlow && !mtfData && !error && (
            <div className="es">
              <div className="ei">◈</div>
              <div className="et">VMC + MF + MTF</div>
              <div className="esb">
                <strong>▶ Full Research</strong> — AI-powered backtest report<br />
                <strong>⚡ Backtest</strong> — fast stats, no AI call<br />
                <strong>💰 Money Flow</strong> — OBV · CMF · MFI · Volume<br />
                <strong>🕐 MTF</strong> — multi-timeframe confirmation<br /><br />
                {htfs.length > 0
                  ? <span>On <strong>{timeframe}</strong>, higher timeframes checked: <strong>{htfs.join(" + ")}</strong></span>
                  : <span><strong>{timeframe}</strong> is the highest timeframe — no HTF filter.</span>
                }
              </div>
            </div>
          )}

          {(r || moneyFlow || mtfData) && !loading && (
            <>
              <div style={{ display:"flex",alignItems:"center",gap:16,marginBottom:16,flexWrap:"wrap" }}>
                <div className="sl2" style={{ margin:0 }}>
                  {asset} / {timeframe}{r?` — ${r.candles_used} candles`:""}
                </div>
                <div className="mt">
                  {r?.mode==="full" && <button className={`mb ${activeTab==="report"?"on":""}`} onClick={()=>setActiveTab("report")}>AI Report</button>}
                  {r && <button className={`mb ${activeTab==="trades"?"on":""}`} onClick={()=>setActiveTab("trades")}>Trades</button>}
                  {moneyFlow && <button className={`mb ${activeTab==="moneyflow"?"on":""}`}
                    onClick={()=>setActiveTab("moneyflow")}
                    style={{ borderColor:activeTab==="moneyflow"?"var(--purple)":"var(--border)",
                             color:activeTab==="moneyflow"?"var(--purple)":"var(--muted)" }}>
                    💰 Money Flow
                  </button>}
                  {mtfData && <button className={`mb ${activeTab==="mtf"?"on":""}`}
                    onClick={()=>setActiveTab("mtf")}
                    style={{ borderColor:activeTab==="mtf"?"var(--orange)":"var(--border)",
                             color:activeTab==="mtf"?"var(--orange)":"var(--muted)" }}>
                    🕐 MTF
                  </button>}
                </div>
              </div>

              {/* Backtest stats */}
              {bt && activeTab!=="moneyflow" && activeTab!=="mtf" && (
                <Card icon="▤" bg="rgba(0,204,255,0.1)" title="Backtest Performance — Real Data" full>
                  <div className="sg">
                    {[["Total Trades",bt.total_trades,"var(--text)"],
                      ["Win Rate",`${bt.win_rate}%`,bt.win_rate>=55?"var(--green)":bt.win_rate>=45?"var(--gold)":"var(--red)"],
                      ["Avg R:R",bt.avg_rr,"var(--blue)"],
                      ["Profit Factor",bt.profit_factor??"—",bt.profit_factor>=1.5?"var(--green)":bt.profit_factor>=1?"var(--gold)":"var(--red)"],
                      ["Max Drawdown",`${bt.max_drawdown}%`,"var(--red)"],
                      ["Total PnL",`${bt.total_pnl>0?"+":""}${bt.total_pnl}%`,bt.total_pnl>=0?"var(--green)":"var(--red)"],
                      ["Wins",bt.win_count,"var(--green)"],["Losses",bt.loss_count,"var(--red)"],
                    ].map(([l,v,c])=>(
                      <div key={l} className="si">
                        <div className="sl">{l}</div>
                        <div className="sv" style={{ color:c,fontSize:String(v).length>6?14:18 }}>{v}</div>
                      </div>
                    ))}
                  </div>
                  {bt.by_signal && Object.keys(bt.by_signal).length>0 && (
                    <><h4 style={{ marginTop:16 }}>Win Rate by Signal Type</h4><BySignal bySignal={bt.by_signal} /></>
                  )}
                </Card>
              )}

              {/* Money Flow Tab */}
              {activeTab==="moneyflow" && (
                <Card icon="💰" bg="rgba(153,102,255,0.15)" title="Money Flow Analysis — Latest Closed Candle" full>
                  <MoneyFlowPanel mf={moneyFlow} />
                </Card>
              )}

              {/* MTF Tab */}
              {activeTab==="mtf" && (
                <Card icon="🕐" bg="rgba(255,102,51,0.15)" title={`Multi-Timeframe Confirmation — ${SIGNAL_TYPES.find(s=>s.key===activeSig)?.label || activeSig}`} full>
                  <MTFPanel mtf={mtfData} timeframe={timeframe} signal={activeSig} />
                </Card>
              )}

              {/* AI Report */}
              {activeTab==="report" && ai && (
                <>
                  <div className="grid2" style={{ marginTop:14 }}>
                    <Card icon="◈" bg="rgba(0,255,136,0.1)" title="Overview">
                      <p>{ai.overview?.summary}</p>
                      <div className="ob">✓ Best For</div>
                      <p>{ai.overview?.bestFor}</p>
                      <div style={{ marginTop:8 }}>
                        <span style={{ fontFamily:"var(--mono)",fontSize:10,color:"var(--muted)" }}>RELIABILITY: </span>
                        <span style={{ color:"var(--green)",fontFamily:"var(--mono)",fontSize:11 }}>{ai.overview?.reliability}</span>
                      </div>
                    </Card>
                    <Card icon="≋" bg="rgba(0,204,255,0.1)" title="Market Context">
                      {[["Trending",ai.marketContext?.trendingMarkets,"var(--green)"],
                        ["Ranging",ai.marketContext?.rangingMarkets,"var(--red)"],
                        ["Volume & MFI",ai.marketContext?.volumeImportance,"var(--blue)"],
                        ["HTF Alignment",ai.marketContext?.correlation,"var(--purple)"],
                      ].map(([l,v,c])=>(
                        <div key={l} style={{ marginBottom:9,paddingBottom:9,borderBottom:"1px solid var(--border)" }}>
                          <div style={{ fontFamily:"var(--mono)",fontSize:9,color:c,marginBottom:3 }}>◆ {l}</div>
                          <div style={{ fontSize:12 }}>{v}</div>
                        </div>
                      ))}
                    </Card>
                  </div>
                  <div className="grid2">
                    <Card icon="↑" bg="rgba(0,255,136,0.1)" title="Bullish Analysis">
                      <div className="ob">▲ Bullish Setup</div>
                      <p>{ai.signalAnalysis?.bullishSetup}</p>
                      <div style={{ marginTop:8 }}>
                        <div style={{ fontFamily:"var(--mono)",fontSize:9,color:"var(--gold)",marginBottom:4 }}>◆ GOLD DOT</div>
                        <p style={{ fontSize:12 }}>{ai.signalAnalysis?.goldDotSignificance}</p>
                      </div>
                    </Card>
                    <Card icon="↓" bg="rgba(255,51,85,0.1)" title="Bearish Analysis">
                      <div className="wb">▼ Bearish Setup</div>
                      <p>{ai.signalAnalysis?.bearishSetup}</p>
                      <div style={{ marginTop:8 }}>
                        <div style={{ fontFamily:"var(--mono)",fontSize:9,color:"var(--blue)",marginBottom:4 }}>◆ DIVERGENCE</div>
                        <p style={{ fontSize:12 }}>{ai.signalAnalysis?.divergenceStrength}</p>
                      </div>
                    </Card>
                  </div>
                  <div className="grid2">
                    <Card icon="→" bg="rgba(153,102,255,0.1)" title="Entry Rules">
                      <ul className="rl">{ai.strategy?.entryRules?.map((r,i)=>(
                        <li key={i} className="ri"><span className="rn">E{i+1}</span><span>{r}</span></li>
                      ))}</ul>
                    </Card>
                    <Card icon="✕" bg="rgba(255,215,0,0.1)" title="Exit & Filters">
                      <h4>Exit</h4>
                      <ul className="rl">{ai.strategy?.exitRules?.map((r,i)=>(
                        <li key={i} className="ri">
                          <span className="rn" style={{ color:"var(--gold)",background:"rgba(255,215,0,0.08)",borderColor:"rgba(255,215,0,0.2)" }}>X{i+1}</span><span>{r}</span>
                        </li>
                      ))}</ul>
                      <h4 style={{ marginTop:12 }}>Filters</h4>
                      <ul className="rl">{ai.strategy?.filters?.map((r,i)=>(
                        <li key={i} className="ri">
                          <span className="rn" style={{ color:"var(--blue)",background:"rgba(0,204,255,0.08)",borderColor:"rgba(0,204,255,0.2)" }}>F{i+1}</span><span>{r}</span>
                        </li>
                      ))}</ul>
                      <div style={{ marginTop:10,padding:"8px 12px",background:"var(--card2)",borderRadius:6 }}>
                        <div style={{ fontFamily:"var(--mono)",fontSize:9,color:"var(--muted)",marginBottom:4 }}>OPTIMAL SETTINGS</div>
                        <div style={{ fontFamily:"var(--mono)",fontSize:11,color:"var(--green)" }}>{ai.strategy?.optimalSettings}</div>
                      </div>
                    </Card>
                  </div>
                  <Card icon="⚠" bg="rgba(255,51,85,0.1)" title="Risk Management" full>
                    <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:10 }}>
                      {[["Stop Loss",ai.riskManagement?.stopLoss,"var(--red)"],
                        ["Position Sizing",ai.riskManagement?.positionSizing,"var(--green)"],
                        ["Avoid When",ai.riskManagement?.avoidWhen,"var(--gold)"],
                        ["Max Drawdown",ai.riskManagement?.maxDrawdown,"var(--blue)"],
                      ].map(([l,v,c])=>(
                        <div key={l} style={{ padding:"10px 12px",background:"var(--card2)",borderRadius:6 }}>
                          <div style={{ fontFamily:"var(--mono)",fontSize:9,color:"var(--muted)",marginBottom:4 }}>{l}</div>
                          <div style={{ fontSize:12,color:c }}>{v}</div>
                        </div>
                      ))}
                    </div>
                  </Card>
                  <Card icon="★" bg="rgba(255,215,0,0.15)" title="AI Verdict" full>
                    <div style={{ fontFamily:"var(--mono)",fontSize:13,lineHeight:1.8,borderLeft:"3px solid var(--gold)",paddingLeft:16 }}>
                      {ai.verdict}
                    </div>
                  </Card>
                </>
              )}

              {/* Trades */}
              {activeTab==="trades" && r && (
                <Card icon="↗" bg="rgba(255,215,0,0.1)" title="Recent Simulated Trades" full>
                  <TradesTable trades={r.recent_trades} />
                </Card>
              )}

              <div style={{ textAlign:"center",padding:"20px 0 8px",fontFamily:"var(--mono)",fontSize:10,color:"var(--muted)" }}>
                ⚠ Backtested results are simulated. Not financial advice.
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}