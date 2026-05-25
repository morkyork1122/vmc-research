import { useState, useRef, useEffect } from "react";

const API_BASE = "https://vmc-research-production.up.railway.app/api";

const ASSETS = ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT","DOGE/USDT","AVAX/USDT","MATIC/USDT"];
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

const LOADING_STEPS = [
  "Connecting to HTX","Fetching OHLCV candles","Computing WaveTrend",
  "Detecting divergences","Computing money flow","Running backtest",
  "Calculating stats","Sending to Claude","Generating AI report",
];

const QUICK_QUESTIONS = [
  "Should I take this signal?",
  "What's the risk on this trade?",
  "Is money flow confirming?",
  "What does the daily timeframe say?",
  "What's the best entry price?",
  "When should I exit?",
];

const S = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Bebas+Neue&family=Inter:wght@300;400;500;600&display=swap');
  *{box-sizing:border-box;margin:0;padding:0;}
  :root{
    --bg:#06060e;--surface:#0c0c18;--card:#10101f;--card2:#14142a;
    --border:#1e1e38;--green:#00ff88;--red:#ff3355;--gold:#ffd700;
    --blue:#00ccff;--purple:#9966ff;--orange:#ff6633;
    --text:#d4d4f0;--muted:#5a5a8a;
    --mono:'Space Mono',monospace;--sans:'Inter',sans-serif;--display:'Bebas Neue',sans-serif;
  }
  body{background:var(--bg);color:var(--text);font-family:var(--sans);}
  .app{min-height:100vh;display:flex;flex-direction:column;background:var(--bg);
    background-image:radial-gradient(ellipse at 20% 0%,rgba(0,255,136,0.04) 0%,transparent 60%),
      radial-gradient(ellipse at 80% 100%,rgba(153,102,255,0.04) 0%,transparent 60%);}
  .header{border-bottom:1px solid var(--border);padding:12px 20px;display:flex;
    align-items:center;gap:12px;background:rgba(12,12,24,0.95);
    backdrop-filter:blur(10px);position:sticky;top:0;z-index:20;flex-wrap:wrap;}
  .logo{font-family:var(--display);font-size:20px;letter-spacing:2px;color:var(--green);white-space:nowrap;}
  .logo span{color:var(--muted);}
  .hdiv{width:1px;height:24px;background:var(--border);}
  .tag{font-family:var(--mono);font-size:9px;padding:3px 7px;border-radius:3px;
    border:1px solid var(--green);color:var(--green);text-transform:uppercase;letter-spacing:1px;}
  .chat-toggle{margin-left:auto;padding:6px 14px;background:rgba(153,102,255,0.15);
    color:var(--purple);border:1px solid var(--purple);border-radius:5px;
    font-family:var(--mono);font-size:10px;cursor:pointer;transition:all 0.2s;white-space:nowrap;}
  .chat-toggle:hover{background:rgba(153,102,255,0.25);}
  .chat-toggle.active{background:var(--purple);color:#000;}
  .body-wrap{display:flex;flex:1;overflow:hidden;}
  .main-panel{flex:1;overflow-y:auto;padding:16px 20px;min-width:0;}
  .controls{padding:12px 20px;display:flex;gap:10px;align-items:flex-end;
    flex-wrap:wrap;background:var(--surface);border-bottom:1px solid var(--border);}
  .cg{display:flex;flex-direction:column;gap:5px;}
  .cl{font-family:var(--mono);font-size:9px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);}
  .sw{position:relative;}
  select{background:var(--card);border:1px solid var(--border);color:var(--text);
    font-family:var(--mono);font-size:12px;padding:7px 32px 7px 10px;
    border-radius:5px;cursor:pointer;appearance:none;outline:none;transition:border-color 0.2s;min-width:110px;}
  select:hover,select:focus{border-color:var(--green);}
  .sa{position:absolute;right:9px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none;font-size:9px;}
  .sigs{display:flex;gap:5px;flex-wrap:wrap;align-items:center;}
  .chip{display:flex;align-items:center;gap:4px;padding:5px 8px;border-radius:4px;
    background:var(--card);border:1px solid var(--border);cursor:pointer;
    font-family:var(--mono);font-size:9px;transition:all 0.15s;user-select:none;}
  .chip.on{border-color:currentColor;background:rgba(0,0,0,0.3);}
  .chip .d{width:5px;height:5px;border-radius:50%;}
  .btn{padding:8px 18px;border:none;border-radius:5px;font-family:var(--mono);
    font-size:11px;font-weight:700;letter-spacing:1px;cursor:pointer;transition:all 0.2s;white-space:nowrap;align-self:flex-end;}
  .btn-g{background:var(--green);color:#000;}
  .btn-g:hover{background:#00e87a;transform:translateY(-1px);}
  .btn-b{background:transparent;color:var(--blue);border:1px solid var(--blue);}
  .btn-b:hover{background:rgba(0,204,255,0.08);}
  .btn-p{background:transparent;color:var(--purple);border:1px solid var(--purple);}
  .btn-p:hover{background:rgba(153,102,255,0.08);}
  .btn-o{background:transparent;color:var(--orange);border:1px solid var(--orange);}
  .btn-o:hover{background:rgba(255,102,51,0.08);}
  .btn:disabled{opacity:0.4;cursor:not-allowed;transform:none;}
  .legend{display:grid;grid-template-columns:repeat(7,1fr);gap:7px;margin-bottom:16px;}
  @media(max-width:900px){.legend{grid-template-columns:repeat(3,1fr);}}
  .lc{background:var(--card);border:1px solid var(--border);border-radius:7px;
    padding:9px;position:relative;overflow:hidden;}
  .lc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent,var(--green));}
  .lt{font-family:var(--mono);font-size:9px;font-weight:700;color:var(--accent,var(--green));margin-bottom:2px;}
  .ld{font-size:9px;color:var(--muted);line-height:1.4;}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;}
  @media(max-width:700px){.grid2{grid-template-columns:1fr;}}
  .fw{grid-column:1/-1;}
  .card{background:var(--card);border:1px solid var(--border);border-radius:9px;padding:16px;}
  .ch{display:flex;align-items:center;gap:9px;margin-bottom:12px;padding-bottom:9px;border-bottom:1px solid var(--border);}
  .ci{width:24px;height:24px;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;}
  .ct{font-family:var(--mono);font-size:9px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);}
  .cb{font-size:12px;line-height:1.7;color:var(--text);}
  .cb p{margin-bottom:7px;}
  .cb p:last-child{margin-bottom:0;}
  .sg{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:7px;}
  .si{background:var(--card2);border-radius:5px;padding:9px 11px;}
  .sl{font-family:var(--mono);font-size:8px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:3px;}
  .sv{font-family:var(--mono);font-size:16px;font-weight:700;}
  .rl{list-style:none;}
  .ri{display:flex;gap:9px;padding:6px 0;border-bottom:1px solid var(--border);font-size:11px;line-height:1.5;}
  .ri:last-child{border-bottom:none;}
  .rn{font-family:var(--mono);font-size:8px;color:var(--green);background:rgba(0,255,136,0.08);
    border:1px solid rgba(0,255,136,0.2);border-radius:3px;padding:1px 5px;height:fit-content;margin-top:2px;flex-shrink:0;}
  .wb{display:inline-flex;align-items:center;gap:4px;background:rgba(255,51,85,0.08);
    border:1px solid rgba(255,51,85,0.25);border-radius:3px;padding:2px 7px;
    font-family:var(--mono);font-size:9px;color:var(--red);margin-bottom:9px;}
  .ob{display:inline-flex;align-items:center;gap:4px;background:rgba(0,255,136,0.08);
    border:1px solid rgba(0,255,136,0.25);border-radius:3px;padding:2px 7px;
    font-family:var(--mono);font-size:9px;color:var(--green);margin-bottom:9px;}
  .lw{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:50px 20px;gap:18px;}
  .spin{width:40px;height:40px;border:2px solid var(--border);border-top-color:var(--green);
    border-radius:50%;animation:spin 0.8s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg);}}
  .steps{display:flex;flex-direction:column;gap:6px;}
  .step{font-family:var(--mono);font-size:10px;color:var(--muted);display:flex;align-items:center;gap:7px;transition:color 0.3s;}
  .step.done{color:var(--green);}.step.on{color:var(--text);}
  .step .sd{width:5px;height:5px;border-radius:50%;background:currentColor;flex-shrink:0;}
  .empty{display:flex;flex-direction:column;align-items:center;justify-content:center;
    padding:50px 20px;gap:12px;text-align:center;}
  .ei{font-size:40px;opacity:0.3;}
  .et{font-family:var(--display);font-size:22px;letter-spacing:3px;color:var(--muted);}
  .es{font-size:11px;color:var(--muted);max-width:360px;line-height:1.6;}
  .err{background:rgba(255,51,85,0.05);border:1px solid rgba(255,51,85,0.2);
    border-radius:7px;padding:16px;font-family:var(--mono);font-size:11px;color:var(--red);text-align:center;}
  h4{font-size:11px;font-weight:600;margin-bottom:6px;color:var(--text);}
  .tt{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:10px;}
  .tt th{text-align:left;padding:5px 9px;color:var(--muted);border-bottom:1px solid var(--border);font-size:8px;text-transform:uppercase;letter-spacing:1px;}
  .tt td{padding:6px 9px;border-bottom:1px solid var(--border);}
  .tt tr:last-child td{border-bottom:none;}
  .bw{padding:2px 6px;border-radius:3px;font-size:9px;font-weight:700;}
  .bww{background:rgba(0,255,136,0.15);color:var(--green);}
  .bwl{background:rgba(255,51,85,0.12);color:var(--red);}
  .sl2{font-family:var(--mono);font-size:8px;text-transform:uppercase;letter-spacing:3px;color:var(--muted);margin-bottom:10px;}
  .bsg{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:7px;margin-top:7px;}
  .bsc{background:var(--card2);border-radius:5px;padding:9px;}
  .bsn{font-family:var(--mono);font-size:8px;color:var(--muted);text-transform:uppercase;margin-bottom:5px;}
  .bsw{font-family:var(--mono);font-size:15px;font-weight:700;}
  .bsm{font-family:var(--mono);font-size:8px;color:var(--muted);margin-top:2px;}
  .mt{display:flex;gap:0;margin-left:auto;}
  .mb{padding:4px 10px;font-family:var(--mono);font-size:9px;cursor:pointer;
    border:1px solid var(--border);background:transparent;color:var(--muted);transition:all 0.15s;}
  .mb:first-child{border-radius:4px 0 0 4px;}.mb:last-child{border-radius:0 4px 4px 0;}
  .mb.on{background:var(--card2);color:var(--green);border-color:var(--green);}
  .ticker{font-family:var(--mono);font-size:10px;color:var(--muted);padding:4px 20px;
    background:var(--surface);border-bottom:1px solid var(--border);display:flex;gap:20px;}
  .ti{display:flex;gap:5px;}
  .mfg{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:12px;}
  .mfgi{background:var(--card2);border-radius:7px;padding:10px;text-align:center;}
  .mfgl{font-family:var(--mono);font-size:8px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:5px;}
  .mfgv{font-family:var(--mono);font-size:18px;font-weight:700;}
  .mfgs{font-size:9px;color:var(--muted);margin-top:2px;}
  .mfsb{height:5px;border-radius:3px;background:var(--border);overflow:hidden;margin:7px 0;}
  .mfsf{height:100%;border-radius:3px;transition:width 0.5s ease;}
  .bb{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:16px;
    font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:1px;margin-bottom:12px;}
  .sb{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:4px;
    font-family:var(--mono);font-size:10px;font-weight:700;margin-left:7px;}
  .obr{display:flex;align-items:center;gap:9px;padding:7px 10px;background:var(--card2);border-radius:5px;margin-bottom:7px;}
  .obl{font-family:var(--mono);font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;min-width:70px;}
  .obbw{flex:1;height:3px;background:var(--border);border-radius:2px;overflow:hidden;}
  .obbf{height:100%;border-radius:2px;}
  .obv{font-family:var(--mono);font-size:10px;min-width:55px;text-align:right;}
  .mfr{display:flex;flex-direction:column;gap:5px;margin-top:10px;}
  .mfri{font-size:11px;padding:5px 9px;background:var(--card2);border-radius:4px;line-height:1.4;}

  /* ── Chat Panel ── */
  .chat-panel{width:340px;border-left:1px solid var(--border);background:var(--surface);
    display:flex;flex-direction:column;height:calc(100vh - 45px);position:sticky;top:45px;flex-shrink:0;}
  .chat-panel.hidden{display:none;}
  .cp-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;}
  .cp-title{font-family:var(--mono);font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--purple);}
  .cp-sub{font-size:10px;color:var(--muted);margin-top:1px;}
  .cp-messages{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:10px;}
  .msg{max-width:90%;padding:10px 12px;border-radius:8px;font-size:12px;line-height:1.6;}
  .msg-user{background:rgba(153,102,255,0.15);border:1px solid rgba(153,102,255,0.3);
    color:var(--text);align-self:flex-end;border-radius:8px 8px 2px 8px;}
  .msg-ai{background:var(--card);border:1px solid var(--border);
    color:var(--text);align-self:flex-start;border-radius:8px 8px 8px 2px;}
  .msg-ai .ai-label{font-family:var(--mono);font-size:8px;color:var(--purple);
    text-transform:uppercase;letter-spacing:1px;margin-bottom:5px;}
  .msg-thinking{opacity:0.5;font-style:italic;}
  .cp-quick{padding:8px 12px;border-top:1px solid var(--border);display:flex;flex-wrap:wrap;gap:5px;}
  .qq{padding:4px 8px;background:var(--card);border:1px solid var(--border);
    border-radius:12px;font-size:10px;cursor:pointer;color:var(--muted);transition:all 0.15s;}
  .qq:hover{border-color:var(--purple);color:var(--purple);}
  .cp-input{padding:10px 12px;border-top:1px solid var(--border);display:flex;gap:8px;align-items:flex-end;}
  .cp-input textarea{flex:1;background:var(--card);border:1px solid var(--border);
    color:var(--text);font-family:var(--sans);font-size:12px;padding:8px 10px;
    border-radius:6px;resize:none;outline:none;line-height:1.5;max-height:80px;}
  .cp-input textarea:focus{border-color:var(--purple);}
  .cp-input textarea::placeholder{color:var(--muted);}
  .send-btn{padding:8px 12px;background:var(--purple);color:#fff;border:none;
    border-radius:6px;cursor:pointer;font-size:14px;transition:all 0.2s;flex-shrink:0;}
  .send-btn:hover{background:#8855ee;}
  .send-btn:disabled{opacity:0.4;cursor:not-allowed;}
  .cp-ctx{padding:8px 12px;background:rgba(153,102,255,0.05);border-top:1px solid var(--border);
    font-family:var(--mono);font-size:9px;color:var(--muted);}
  .cp-ctx span{color:var(--purple);}
`;

function LoadingView({ step }) {
  return (
    <div className="lw">
      <div className="spin" />
      <div className="steps">
        {LOADING_STEPS.map((s,i) => (
          <div key={i} className={`step ${i<step?"done":i===step?"on":""}`}>
            <span className="sd" />{i<step?"✓ ":i===step?"▶ ":"○ "}{s}
          </div>
        ))}
      </div>
    </div>
  );
}

function Card({ icon, bg, title, children, full }) {
  return (
    <div className={`card${full?" fw":""}`}>
      <div className="ch">
        <div className="ci" style={{background:bg}}>{icon}</div>
        <div className="ct">{title}</div>
      </div>
      <div className="cb">{children}</div>
    </div>
  );
}

function BySig({ by }) {
  if (!by||!Object.keys(by).length) return null;
  return (
    <div className="bsg">
      {Object.entries(by).map(([sig,d]) => {
        const s=SIGNAL_TYPES.find(x=>x.key===sig);
        const wr=d.win_rate;
        const c=wr>=55?"var(--green)":wr>=45?"var(--gold)":"var(--red)";
        return (
          <div key={sig} className="bsc">
            <div className="bsn">{s?.label||sig}</div>
            <div className="bsw" style={{color:c}}>{wr}%</div>
            <div className="bsm">{d.total} trades · {d.avg_pnl>0?"+":""}{d.avg_pnl}%</div>
          </div>
        );
      })}
    </div>
  );
}

function TradesTable({ trades }) {
  if (!trades?.length) return <p style={{color:"var(--muted)",fontSize:11}}>No trades.</p>;
  return (
    <div style={{overflowX:"auto"}}>
      <table className="tt">
        <thead><tr>
          <th>Signal</th><th>Dir</th><th>Entry</th><th>Exit</th>
          <th>SL</th><th>TP</th><th>WT2</th><th>PnL</th><th>Result</th>
        </tr></thead>
        <tbody>
          {trades.map((t,i) => {
            const s=SIGNAL_TYPES.find(x=>x.key===t.signal_type);
            return (
              <tr key={i}>
                <td style={{color:s?.color||"var(--text)"}}>{s?.label||t.signal_type}</td>
                <td style={{color:t.direction==="long"?"var(--green)":"var(--red)"}}>
                  {t.direction==="long"?"▲":"▼"} {t.direction}
                </td>
                <td>{t.entry_price}</td><td>{t.exit_price}</td>
                <td style={{color:"var(--red)"}}>{t.stop_loss}</td>
                <td style={{color:"var(--green)"}}>{t.take_profit}</td>
                <td style={{color:t.wt2_at_entry<-53?"var(--green)":t.wt2_at_entry>53?"var(--red)":"var(--text)"}}>{t.wt2_at_entry}</td>
                <td style={{color:t.pnl_pct>=0?"var(--green)":"var(--red)"}}>{t.pnl_pct>=0?"+":""}{t.pnl_pct}%</td>
                <td><span className={`bw ${t.result==="win"?"bww":"bwl"}`}>{t.result}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function MFPanel({ mf }) {
  if (!mf) return <p style={{color:"var(--muted)",fontSize:11,textAlign:"center",padding:16}}>Click 💰 Money Flow to analyse.</p>;
  const bC=mf.mf_bias==="BULLISH"?"var(--green)":mf.mf_bias==="BEARISH"?"var(--red)":"var(--muted)";
  const sC=mf.strength==="STRONG"?"var(--green)":mf.strength==="MODERATE"?"var(--gold)":"var(--red)";
  const cmf=mf.cmf||0; const mfi=mf.mfi||50; const vr=mf.vol_ratio||1;
  return (
    <div>
      <div style={{display:"flex",alignItems:"center",marginBottom:12,flexWrap:"wrap",gap:7}}>
        <div className="bb" style={{background:`${bC}15`,border:`1px solid ${bC}40`,color:bC}}>
          {mf.mf_bias==="BULLISH"?"▲":mf.mf_bias==="BEARISH"?"▼":"━"} {mf.mf_bias} FLOW
        </div>
        <div className="sb" style={{background:`${sC}15`,border:`1px solid ${sC}40`,color:sC}}>◆ {mf.strength}</div>
        <div style={{fontFamily:"var(--mono)",fontSize:9,color:"var(--muted)",marginLeft:"auto"}}>{mf.confluence||0}/5 confirming</div>
      </div>
      <div style={{marginBottom:14}}>
        <div style={{display:"flex",justifyContent:"space-between",marginBottom:3}}>
          <span style={{fontFamily:"var(--mono)",fontSize:8,color:"var(--muted)",textTransform:"uppercase",letterSpacing:1}}>Confidence Score</span>
          <span style={{fontFamily:"var(--mono)",fontSize:11,color:sC,fontWeight:700}}>{mf.score}/100</span>
        </div>
        <div className="mfsb"><div className="mfsf" style={{width:`${mf.score||50}%`,background:sC}} /></div>
      </div>
      <div className="mfg">
        <div className="mfgi">
          <div className="mfgl">CMF</div>
          <div className="mfgv" style={{color:cmf>0?"var(--green)":"var(--red)"}}>{cmf>0?"+":""}{cmf.toFixed(3)}</div>
          <div className="mfgs">{cmf>0.1?"Inst. Buying":cmf<-0.1?"Inst. Selling":"Neutral"}</div>
        </div>
        <div className="mfgi">
          <div className="mfgl">MFI</div>
          <div className="mfgv" style={{color:mfi<30?"var(--green)":mfi>70?"var(--red)":"var(--gold)"}}>{mfi.toFixed(0)}</div>
          <div className="mfgs">{mfi<30?"Oversold":mfi>70?"Overbought":"Neutral"}</div>
        </div>
        <div className="mfgi">
          <div className="mfgl">Volume</div>
          <div className="mfgv" style={{color:mf.vol_spike?"var(--gold)":"var(--blue)"}}>{vr.toFixed(1)}x</div>
          <div className="mfgs">{mf.vol_spike?"🔥 Spike":"Normal"}</div>
        </div>
      </div>
      {[["CMF",Math.min(100,Math.abs(cmf*500)),cmf>0?"var(--green)":"var(--red)",`${cmf>0?"+":""}${cmf.toFixed(3)}`],
        ["MFI",mfi,mfi<30?"var(--green)":mfi>70?"var(--red)":"var(--gold)",`${mfi.toFixed(0)}`],
        ["OBV",(mf.obv_trend||"").includes("Rising")?70:30,(mf.obv_trend||"").includes("Rising")?"var(--green)":"var(--red)",mf.obv_trend||"—"],
        ["Volume",Math.min(100,(vr/4)*100),mf.vol_spike?"var(--gold)":"var(--blue)",`${vr.toFixed(1)}x avg`],
      ].map(([l,p,c,v])=>(
        <div key={l} className="obr">
          <span className="obl">{l}</span>
          <div className="obbw"><div className="obbf" style={{width:`${p}%`,background:c}} /></div>
          <span className="obv" style={{color:c}}>{v}</span>
        </div>
      ))}
      {mf.reasons?.length>0&&<><h4 style={{marginTop:12}}>Analysis</h4><div className="mfr">{mf.reasons.map((r,i)=><div key={i} className="mfri">{r}</div>)}</div></>}
    </div>
  );
}

function MTFPanel({ mtf }) {
  if (!mtf) return <p style={{color:"var(--muted)",fontSize:11,textAlign:"center",padding:16}}>Click 🔭 MTF to analyse.</p>;
  const cC=mtf.htf_confirmation==="CONFIRMED"?"var(--green)":mtf.htf_confirmation==="AGAINST"?"var(--red)":"var(--gold)";
  const cE=mtf.htf_confirmation==="CONFIRMED"?"✅":mtf.htf_confirmation==="AGAINST"?"❌":"⚡";
  const overall=mtf.overall_score||50;
  const oC=overall>=75?"var(--green)":overall>=60?"var(--gold)":"var(--red)";
  return (
    <div>
      <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:14,flexWrap:"wrap"}}>
        <div className="bb" style={{background:`${cC}15`,border:`1px solid ${cC}40`,color:cC}}>
          {cE} {mtf.htf_label||mtf.htf_timeframe}: {mtf.htf_confirmation}
        </div>
        <div style={{fontFamily:"var(--mono)",fontSize:9,color:"var(--muted)"}}>{mtf.htf_score||0}/100</div>
      </div>
      <div style={{marginBottom:14}}>
        <div style={{display:"flex",justifyContent:"space-between",marginBottom:3}}>
          <span style={{fontFamily:"var(--mono)",fontSize:8,color:"var(--muted)",textTransform:"uppercase",letterSpacing:1}}>Overall Grade</span>
          <span style={{fontFamily:"var(--mono)",fontSize:11,color:oC,fontWeight:700}}>{overall}/100</span>
        </div>
        <div className="mfsb"><div className="mfsf" style={{width:`${overall}%`,background:oC}} /></div>
        {mtf.grade&&<div style={{fontFamily:"var(--mono)",fontSize:10,color:oC,marginTop:4}}>{mtf.grade}</div>}
      </div>
      <div className="sg">
        {[["HTF Trend",mtf.htf_trend||"—","var(--text)"],
          ["HTF WT2",`${mtf.htf_wt2||0}`,(mtf.htf_wt2||0)<0?"var(--green)":"var(--red)"],
          ["HTF CMF",`${mtf.htf_cmf>=0?"+":""}${(mtf.htf_cmf||0).toFixed(3)}`,(mtf.htf_cmf||0)>0?"var(--green)":"var(--red)"],
          ["HTF OBV",mtf.htf_obv_trend||"—",(mtf.htf_obv_trend||"").includes("Rising")?"var(--green)":"var(--red)"],
        ].map(([l,v,c])=>(
          <div key={l} className="si">
            <div className="sl">{l}</div>
            <div className="sv" style={{color:c,fontSize:13}}>{v}</div>
          </div>
        ))}
      </div>
      {mtf.mf_bias&&<div style={{marginTop:12,padding:"8px 11px",background:"var(--card2)",borderRadius:6}}>
        <div style={{fontFamily:"var(--mono)",fontSize:8,color:"var(--muted)",marginBottom:3}}>PRIMARY TF MONEY FLOW</div>
        <div style={{fontFamily:"var(--mono)",fontSize:11,color:mtf.mf_bias==="BULLISH"?"var(--green)":mtf.mf_bias==="BEARISH"?"var(--red)":"var(--muted)"}}>
          {mtf.mf_bias} — {mtf.mf_strength} ({mtf.mf_score}/100)
        </div>
      </div>}
      {mtf.htf_reasons?.length>0&&<>
        <h4 style={{marginTop:12}}>HTF Analysis</h4>
        <div className="mfr">{mtf.htf_reasons.map((r,i)=><div key={i} className="mfri">{r}</div>)}</div>
      </>}
      {mtf.filter_reason&&mtf.htf_confirmation==="AGAINST"&&
        <div style={{marginTop:10,padding:"8px 11px",background:"rgba(255,51,85,0.08)",border:"1px solid rgba(255,51,85,0.25)",borderRadius:6,fontFamily:"var(--mono)",fontSize:10,color:"var(--red)"}}>
          🚫 {mtf.filter_reason}
        </div>}
    </div>
  );
}

// ── Chat Panel Component ──────────────────────────────────────────────────────

function ChatPanel({ visible, asset, timeframe, activeSig, btStats, mfData, mtfData, latestBar }) {
  const [messages, setMessages] = useState([
    { role: "ai", content: "Hi! I'm your VMC Cipher B analyst. Ask me anything about the current signals, money flow, or whether to take a trade. I have access to all the data on your dashboard." }
  ]);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const hasContext = btStats || mfData || mtfData;

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;
    const userMsg = text.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);
    setMessages(prev => [...prev, { role: "ai", content: "...", thinking: true }]);

    try {
      const history = messages
        .filter(m => !m.thinking)
        .map(m => ({ role: m.role === "ai" ? "assistant" : "user", content: m.content }));

      const resp = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message:        userMsg,
          symbol:         asset,
          timeframe:      timeframe,
          signal_type:    activeSig,
          backtest_stats: btStats,
          money_flow:     mfData,
          mtf:            mtfData,
          latest_bar:     latestBar,
          history:        history,
        }),
      });

      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      const data = await resp.json();
      setMessages(prev => [...prev.slice(0, -1), { role: "ai", content: data.response }]);
    } catch (err) {
      setMessages(prev => [...prev.slice(0, -1), {
        role: "ai",
        content: `Sorry, I couldn't connect to the AI. Make sure your Anthropic API key has credits. Error: ${err.message}`,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  if (!visible) return null;

  return (
    <div className="chat-panel">
      <div className="cp-header">
        <div>
          <div className="cp-title">🤖 AI Analyst</div>
          <div className="cp-sub">{asset} · {timeframe}</div>
        </div>
      </div>

      <div className="cp-messages">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role === "user" ? "msg-user" : "msg-ai"} ${m.thinking ? "msg-thinking" : ""}`}>
            {m.role === "ai" && <div className="ai-label">AI Analyst</div>}
            {m.content}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Context indicator */}
      <div className="cp-ctx">
        Context:{" "}
        <span>{btStats ? "✓ Backtest" : "○ Backtest"}</span>{" · "}
        <span>{mfData ? "✓ MoneyFlow" : "○ MoneyFlow"}</span>{" · "}
        <span>{mtfData ? "✓ MTF" : "○ MTF"}</span>
        {!hasContext && <span style={{color:"var(--red)"}}> — Run analysis first for best results</span>}
      </div>

      {/* Quick questions */}
      <div className="cp-quick">
        {QUICK_QUESTIONS.map((q, i) => (
          <button key={i} className="qq" onClick={() => sendMessage(q)}>{q}</button>
        ))}
      </div>

      {/* Input */}
      <div className="cp-input">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask anything about the signal..."
          rows={2}
          disabled={loading}
        />
        <button className="send-btn" onClick={() => sendMessage(input)} disabled={loading || !input.trim()}>
          {loading ? "⟳" : "↑"}
        </button>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function VMCResearch() {
  const [asset, setAsset]           = useState("BTC/USDT");
  const [timeframe, setTimeframe]   = useState("4H");
  const [sigs, setSigs]             = useState(["green_dot","red_dot","gold_dot","bull_div","bear_div"]);
  const [activeSig, setActiveSig]   = useState("green_dot");
  const [loading, setLoading]       = useState(false);
  const [loadStep, setLoadStep]     = useState(0);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState(null);
  const [tab, setTab]               = useState("report");
  const [mfData, setMfData]         = useState(null);
  const [mfLoading, setMfLoading]   = useState(false);
  const [mtfData, setMtfData]       = useState(null);
  const [mtfLoading, setMtfLoading] = useState(false);
  const [chatOpen, setChatOpen]     = useState(false);
  const stepRef = useRef(0);

  const busy = loading || mfLoading || mtfLoading;
  const toggleSig = k => setSigs(p => p.includes(k)?p.filter(x=>x!==k):[...p,k]);

  const runPipeline = async (mode="full") => {
    setLoading(true); setError(null); setResult(null);
    stepRef.current=0; setLoadStep(0);
    const total=mode==="full"?LOADING_STEPS.length:6;
    const t=setInterval(()=>{ stepRef.current=Math.min(stepRef.current+1,total-1); setLoadStep(stepRef.current); },mode==="full"?2000:1200);
    try {
      const resp=await fetch(`${API_BASE}/${mode==="full"?"research":"backtest"}`,{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({symbol:asset,timeframe,signals:sigs}),
      });
      if(!resp.ok){const e=await resp.json().catch(()=>({}));throw new Error(e.detail||`Error ${resp.status}`);}
      clearInterval(t); setLoadStep(total-1);
      const d=await resp.json();
      setResult({symbol:d.symbol,timeframe:d.timeframe,candles_used:d.candles_used,
        backtest_stats:d.backtest_stats||d.summary,recent_trades:d.recent_trades,
        ai_report:d.ai_report||null,latest_signals:d.latest_signals,mode});
      setTab(mode==="full"?"report":"trades");
    } catch(e){ clearInterval(t); setError(e.message); }
    finally{ setLoading(false); }
  };

  const runMF = async () => {
    setMfLoading(true); setMfData(null);
    try {
      const r=await fetch(`${API_BASE}/money-flow?symbol=${encodeURIComponent(asset)}&timeframe=${timeframe}&signal=${activeSig}`);
      if(!r.ok) throw new Error(`Error ${r.status}`);
      setMfData(await r.json()); setTab("mf");
    } catch(e){ setMfData({error:e.message}); }
    finally{ setMfLoading(false); }
  };

  const runMTF = async () => {
    setMtfLoading(true); setMtfData(null);
    try {
      const r=await fetch(`${API_BASE}/mtf?symbol=${encodeURIComponent(asset)}&timeframe=${timeframe}&signal=${activeSig}`);
      if(!r.ok) throw new Error(`Error ${r.status}`);
      setMtfData(await r.json()); setTab("mtf");
    } catch(e){ setMtfData({error:e.message}); }
    finally{ setMtfLoading(false); }
  };

  const bt=result?.backtest_stats;
  const ai=result?.ai_report;
  const latestBar=result?.latest_signals?.[result.latest_signals.length-1];

  return (
    <>
      <style>{S}</style>
      <div className="app">
        <div className="header">
          <div className="logo">VMC<span>_</span>RESEARCH</div>
          <div className="hdiv" />
          <div className="tag">Real Data</div>
          <div className="tag" style={{borderColor:"var(--purple)",color:"var(--purple)"}}>Cipher B</div>
          <div className="tag" style={{borderColor:"var(--gold)",color:"var(--gold)"}}>AI Powered</div>
          <button className={`chat-toggle ${chatOpen?"active":""}`} onClick={()=>setChatOpen(o=>!o)}>
            {chatOpen?"✕ Close Chat":"🤖 AI Chat"}
          </button>
        </div>

        <div className="ticker">
          {[["BTC","var(--green)","↑"],["ETH","var(--green)","↑"],["SOL","var(--red)","↓"],
            ["BNB","var(--green)","↑"],["DOGE","var(--red)","↓"],["AVAX","var(--green)","↑"]].map(([s,c,a])=>(
            <div key={s} className="ti"><span>{s}/USDT</span><span style={{color:c}}>{a}</span></div>
          ))}
        </div>

        <div className="controls">
          <div className="cg">
            <div className="cl">Asset</div>
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
            <div className="sigs">
              {SIGNAL_TYPES.map(s=>(
                <div key={s.key} className={`chip ${sigs.includes(s.key)?"on":""}`}
                  style={{color:sigs.includes(s.key)?s.color:"var(--muted)"}}
                  onClick={()=>toggleSig(s.key)}>
                  <div className="d" style={{background:s.color}} />{s.label}
                </div>
              ))}
            </div>
          </div>
          <div className="cg">
            <div className="cl">Signal For Analysis</div>
            <div className="sw">
              <select value={activeSig} onChange={e=>setActiveSig(e.target.value)}>
                {SIGNAL_TYPES.map(s=><option key={s.key} value={s.key}>{s.label}</option>)}
              </select><span className="sa">▾</span>
            </div>
          </div>
          <button className="btn btn-g" onClick={()=>runPipeline("full")} disabled={busy}>{loading?"Running...":"▶ Full Research"}</button>
          <button className="btn btn-b" onClick={()=>runPipeline("backtest")} disabled={busy}>⚡ Backtest</button>
          <button className="btn btn-p" onClick={runMF} disabled={busy}>{mfLoading?"Loading...":"💰 Money Flow"}</button>
          <button className="btn btn-o" onClick={runMTF} disabled={busy}>{mtfLoading?"Loading...":"🔭 MTF"}</button>
          <button className="btn" 
  style={{background:"var(--gold)",color:"#000",alignSelf:"flex-end",padding:"8px 18px",border:"none",borderRadius:"5px",fontFamily:"var(--mono)",fontSize:"11px",fontWeight:700,cursor:"pointer"}}
  onClick={runLiveScan} disabled={busy}>
  {mfLoading ? "Scanning..." : "⚡ Live Scan"}
</button>
        </div>
        

        <div className="body-wrap">
          <div className="main-panel">
            <div style={{padding:"12px 0"}}>
              <div className="sl2">Signal Reference</div>
              <div className="legend">
                {SIGNAL_TYPES.map(s=>(
                  <div key={s.key} className="lc" style={{"--accent":s.color}}>
                    <div className="lt">{s.label}</div>
                    <div className="ld">{s.desc}</div>
                  </div>
                ))}
              </div>

              {loading && <LoadingView step={loadStep} />}
              {error&&!loading&&<div className="err">⚠ {error}<div style={{marginTop:8,fontSize:10,color:"var(--muted)"}}>Backend: <code style={{color:"var(--blue)"}}>{API_BASE}</code></div></div>}

              {!loading&&!result&&!mfData&&!mtfData&&!error&&(
                <div className="empty">
                  <div className="ei">◈</div>
                  <div className="et">VMC + MF + MTF + AI</div>
                  <div className="es">
                    Run analysis then ask the <strong>🤖 AI Chat</strong> anything about the signal.<br /><br />
                    <strong>▶ Full Research</strong> — backtest + AI report<br />
                    <strong>⚡ Backtest</strong> — fast, no AI<br />
                    <strong>💰 Money Flow</strong> — OBV · CMF · MFI<br />
                    <strong>🔭 MTF</strong> — higher timeframe check
                  </div>
                </div>
              )}

              {(result||mfData||mtfData)&&!loading&&(
                <>
                  <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:14,flexWrap:"wrap"}}>
                    <div className="sl2" style={{margin:0}}>{asset} / {timeframe}{result?` — ${result.candles_used} candles`:""}</div>
                    <div className="mt">
                      {result?.mode==="full"&&<button className={`mb ${tab==="report"?"on":""}`} onClick={()=>setTab("report")}>AI Report</button>}
                      {result&&<button className={`mb ${tab==="trades"?"on":""}`} onClick={()=>setTab("trades")}>Trades</button>}
                      {mfData&&<button className={`mb ${tab==="mf"?"on":""}`} onClick={()=>setTab("mf")} style={{borderColor:tab==="mf"?"var(--purple)":"var(--border)",color:tab==="mf"?"var(--purple)":"var(--muted)"}}>💰 MFlow</button>}
                      {mtfData&&<button className={`mb ${tab==="mtf"?"on":""}`} onClick={()=>setTab("mtf")} style={{borderColor:tab==="mtf"?"var(--orange)":"var(--border)",color:tab==="mtf"?"var(--orange)":"var(--muted)"}}>🔭 MTF</button>}
                    </div>
                  </div>

                  {bt&&tab!=="mf"&&tab!=="mtf"&&(
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
                            <div className="sv" style={{color:c,fontSize:String(v).length>6?13:16}}>{v}</div>
                          </div>
                        ))}
                      </div>
                      {bt.by_signal&&Object.keys(bt.by_signal).length>0&&<><h4 style={{marginTop:14}}>Win Rate by Signal</h4><BySig by={bt.by_signal} /></>}
                    </Card>
                  )}

                  {tab==="mf"&&<Card icon="💰" bg="rgba(153,102,255,0.15)" title="Money Flow Analysis" full><MFPanel mf={mfData} /></Card>}
                  {tab==="mtf"&&<Card icon="🔭" bg="rgba(255,102,51,0.15)" title={`MTF Confirmation — ${SIGNAL_TYPES.find(s=>s.key===activeSig)?.label||activeSig}`} full><MTFPanel mtf={mtfData} /></Card>}

                  {tab==="report"&&ai&&(
                    <>
                      <div className="grid2" style={{marginTop:12}}>
                        <Card icon="◈" bg="rgba(0,255,136,0.1)" title="Overview">
                          <p>{ai.overview?.summary}</p>
                          <div className="ob">✓ Best For</div>
                          <p>{ai.overview?.bestFor}</p>
                          <div style={{marginTop:7}}><span style={{fontFamily:"var(--mono)",fontSize:9,color:"var(--muted)"}}>RELIABILITY: </span><span style={{color:"var(--green)",fontFamily:"var(--mono)",fontSize:10}}>{ai.overview?.reliability}</span></div>
                        </Card>
                        <Card icon="≋" bg="rgba(0,204,255,0.1)" title="Market Context">
                          {[["Trending",ai.marketContext?.trendingMarkets,"var(--green)"],
                            ["Ranging",ai.marketContext?.rangingMarkets,"var(--red)"],
                            ["Volume",ai.marketContext?.volumeImportance,"var(--blue)"],
                            ["HTF",ai.marketContext?.correlation,"var(--purple)"],
                          ].map(([l,v,c])=>(
                            <div key={l} style={{marginBottom:8,paddingBottom:8,borderBottom:"1px solid var(--border)"}}>
                              <div style={{fontFamily:"var(--mono)",fontSize:8,color:c,marginBottom:2}}>◆ {l}</div>
                              <div style={{fontSize:11}}>{v}</div>
                            </div>
                          ))}
                        </Card>
                      </div>
                      <div className="grid2">
                        <Card icon="↑" bg="rgba(0,255,136,0.1)" title="Bullish Signals">
                          <div className="ob">▲ Bullish Setup</div>
                          <p>{ai.signalAnalysis?.bullishSetup}</p>
                        </Card>
                        <Card icon="↓" bg="rgba(255,51,85,0.1)" title="Bearish Signals">
                          <div className="wb">▼ Bearish Setup</div>
                          <p>{ai.signalAnalysis?.bearishSetup}</p>
                        </Card>
                      </div>
                      <div className="grid2">
                        <Card icon="→" bg="rgba(153,102,255,0.1)" title="Entry Rules">
                          <ul className="rl">{ai.strategy?.entryRules?.map((r,i)=><li key={i} className="ri"><span className="rn">E{i+1}</span><span>{r}</span></li>)}</ul>
                        </Card>
                        <Card icon="✕" bg="rgba(255,215,0,0.1)" title="Exit & Filters">
                          <h4>Exit Rules</h4>
                          <ul className="rl">{ai.strategy?.exitRules?.map((r,i)=><li key={i} className="ri"><span className="rn" style={{color:"var(--gold)",background:"rgba(255,215,0,0.08)",borderColor:"rgba(255,215,0,0.2)"}}>X{i+1}</span><span>{r}</span></li>)}</ul>
                          <h4 style={{marginTop:10}}>Filters</h4>
                          <ul className="rl">{ai.strategy?.filters?.map((r,i)=><li key={i} className="ri"><span className="rn" style={{color:"var(--blue)",background:"rgba(0,204,255,0.08)",borderColor:"rgba(0,204,255,0.2)"}}>F{i+1}</span><span>{r}</span></li>)}</ul>
                        </Card>
                      </div>
                      <Card icon="★" bg="rgba(255,215,0,0.15)" title="AI Verdict" full>
                        <div style={{fontFamily:"var(--mono)",fontSize:12,lineHeight:1.8,borderLeft:"3px solid var(--gold)",paddingLeft:14}}>{ai.verdict}</div>
                      </Card>
                    </>
                  )}

                  {tab==="trades"&&result&&<Card icon="↗" bg="rgba(255,215,0,0.1)" title="Recent Simulated Trades" full><TradesTable trades={result.recent_trades} /></Card>}

                  <div style={{textAlign:"center",padding:"16px 0 6px",fontFamily:"var(--mono)",fontSize:9,color:"var(--muted)"}}>
                    ⚠ Simulated results. Not financial advice.
                  </div>
                </>
              )}
            </div>
          </div>

          <ChatPanel
            visible={chatOpen}
            asset={asset}
            timeframe={timeframe}
            activeSig={activeSig}
            btStats={result?.backtest_stats}
            mfData={mfData}
            mtfData={mtfData}
            latestBar={latestBar}
          />
        </div>
      </div>
    </>
  );
}
const runLiveScan = async () => {
  if (busy) return;
  setMfLoading(true);
  setError(null);
  try {
    const r = await fetch(
      `${API_BASE}/live-scan?symbol=${encodeURIComponent(asset)}&timeframe=${timeframe}&signal=${activeSig}`
    );
    if (!r.ok) throw new Error(`Error ${r.status}`);
    const d = await r.json();

    setMfData(d.money_flow);
    setMtfData(d.mtf ? { ...d.mtf, overall_score: d.overall_score, grade: d.grade } : null);
    setResult(prev => ({
      ...(prev || {}),
      symbol:         d.symbol,
      timeframe:      d.timeframe,
      mode:           "live",
      candles_used:   150,
      backtest_stats: prev?.backtest_stats || null,
      recent_trades:  prev?.recent_trades  || [],
      ai_report:      prev?.ai_report      || null,
      latest_signals: [{ close: d.close, wt1: d.wt1, wt2: d.wt2, timestamp: d.timestamp }],
    }));

    if (d.ai_analysis) {
      setChatOpen(true);
    }
    setTab("mf");
  } catch(e) {
    setError(e.message);
  } finally {
    setMfLoading(false);
  }
};