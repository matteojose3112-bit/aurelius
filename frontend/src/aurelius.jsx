import { useMemo, useState } from 'react'
import {
  Activity, ArrowDownRight, ArrowUpRight, ArrowUpLeft, Bell, BriefcaseBusiness,
  ChartNoAxesCombined, ChevronDown, CircleHelp, Command, Compass, Download,
  Ellipsis, Eye, Landmark, Layers3, Menu, MoreHorizontal, Search, ShieldCheck,
  Sparkles, Wallet, X
} from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
  PieChart, Pie, Cell
} from 'recharts'
import './aurelius.css'

const ranges = ['1M', '3M', '6M', '1Y', 'ALL']
const performance = {
  '1M': [119.2, 120.1, 119.8, 121.4, 122.2, 121.8, 123.5, 124.1, 123.7, 125.2, 126.1, 128.45],
  '3M': [110.4, 112.1, 111.6, 114.8, 113.9, 116.2, 117.1, 115.8, 119.2, 120.1, 123.4, 128.45],
  '6M': [104.2, 106.1, 105.4, 108.3, 110.2, 109.6, 113.1, 115.4, 114.8, 119.2, 123.4, 128.45],
  '1Y': [92.4, 94.1, 96.8, 95.3, 99.2, 101.4, 100.8, 105.1, 108.3, 115.2, 121.1, 128.45],
  ALL: [72.2, 74.1, 77.8, 79.3, 82.2, 86.4, 89.8, 95.1, 102.3, 110.2, 119.1, 128.45],
}
const labels = ['Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov']
const allocation = [
  { name: 'Equities', value: 52, amount: 66800, color: '#b7a4ff' },
  { name: 'Fixed income', value: 21, amount: 26970, color: '#7b9d91' },
  { name: 'Cash', value: 16, amount: 20550, color: '#d6b77c' },
  { name: 'Alternatives', value: 11, amount: 14130, color: '#7897b5' },
]
const holdings = [
  { symbol: 'VTI', name: 'Vanguard Total Stock Market', type: 'US equities', units: '142.00', price: '$286.40', value: '$40,668.80', change: '+2.84%', positive: true, weight: 31.7 },
  { symbol: 'VXUS', name: 'Vanguard Total International', type: 'International equities', units: '310.00', price: '$68.25', value: '$21,157.50', change: '+1.26%', positive: true, weight: 16.5 },
  { symbol: 'BND', name: 'Vanguard Total Bond Market', type: 'Fixed income', units: '255.00', price: '$72.18', value: '$18,405.90', change: '+0.42%', positive: true, weight: 14.3 },
  { symbol: 'SGOV', name: 'iShares 0-3 Month Treasury', type: 'Cash equivalents', units: '205.00', price: '$100.48', value: '$20,598.40', change: '+0.08%', positive: true, weight: 16.0 },
  { symbol: 'GLDM', name: 'SPDR Gold MiniShares', type: 'Alternatives', units: '180.00', price: '$56.72', value: '$10,209.60', change: '−0.31%', positive: false, weight: 8.0 },
]
const activity = [
  { title: 'Monthly contribution', detail: 'Cash account · Nov 14, 2026', amount: '+$1,250.00', positive: true, icon: ArrowDownRight },
  { title: 'VTI · Dividend received', detail: 'Brokerage · Nov 08, 2026', amount: '+$86.42', positive: true, icon: ArrowDownRight },
  { title: 'BND · Distribution', detail: 'Brokerage · Nov 02, 2026', amount: '+$42.18', positive: true, icon: ArrowDownRight },
  { title: 'Portfolio rebalance review', detail: 'Research note · Oct 28, 2026', amount: 'View note', positive: false, icon: Activity },
]
const fmt = n => '$' + Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 })

function App() {
  const [page, setPage] = useState('Overview')
  const [range, setRange] = useState('1Y')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [search, setSearch] = useState('')
  const chartData = useMemo(() => performance[range].map((value, i) => ({ label: labels[i], value })), [range])
  const visibleHoldings = holdings.filter(h => (h.symbol + h.name + h.type).toLowerCase().includes(search.toLowerCase()))
  const navItems = [
    { label: 'Overview', icon: ChartNoAxesCombined },
    { label: 'Portfolio', icon: BriefcaseBusiness },
    { label: 'Activity', icon: Activity },
    { label: 'Research', icon: Compass },
  ]

  return <div className="aur-shell">
    <aside className={'aur-sidebar ' + (mobileOpen ? 'is-open' : '')}>
      <div className="aur-brand">
        <div className="aur-mark"><span /></div>
        <div><div className="aur-brand-name">AURELIUS</div><div className="aur-brand-sub">PORTFOLIO INTELLIGENCE</div></div>
        <button className="aur-icon-btn aur-mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={18}/></button>
      </div>
      <div className="aur-workspace"><div className="aur-avatar">M</div><div><div className="aur-workspace-title">Personal workspace</div><div className="aur-workspace-sub">Demo portfolio</div></div><ChevronDown size={15}/></div>
      <div className="aur-nav-label">WORKSPACE</div>
      <nav className="aur-nav" aria-label="Main navigation">
        {navItems.map(({label, icon: Icon}) => <button key={label} className={'aur-nav-item ' + (page === label ? 'active' : '')} onClick={() => { setPage(label); setMobileOpen(false) }}><Icon size={17}/><span>{label}</span>{label === 'Research' && <span className="aur-nav-soon">NEW</span>}</button>)}
      </nav>
      <div className="aur-nav-label aur-nav-label-lower">MANAGE</div>
      <nav className="aur-nav">
        <button className="aur-nav-item" onClick={() => setPage('Portfolio')}><Layers3 size={17}/><span>Accounts & assets</span></button>
        <button className="aur-nav-item" onClick={() => setPage('Research')}><Sparkles size={17}/><span>Insights</span></button>
      </nav>
      <div className="aur-sidebar-bottom">
        <div className="aur-security"><ShieldCheck size={16}/><div><strong>Read-only demo</strong><span>No accounts connected</span></div></div>
        <button className="aur-nav-item"><CircleHelp size={17}/><span>Help & documentation</span></button>
        <div className="aur-profile"><div className="aur-avatar aur-avatar-small">M</div><div><strong>Demo investor</strong><span>Preview environment</span></div><MoreHorizontal size={17}/></div>
      </div>
    </aside>

    {mobileOpen && <button className="aur-scrim" onClick={() => setMobileOpen(false)} aria-label="Close menu" />}
    <main className="aur-main">
      <header className="aur-topbar">
        <div className="aur-top-left"><button className="aur-icon-btn aur-menu-btn" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={19}/></button><div className="aur-breadcrumb">Workspace <span>/</span> <strong>{page}</strong></div></div>
        <div className="aur-top-actions">
          <div className="aur-search"><Search size={15}/><input aria-label="Search holdings" placeholder="Search anything..." value={search} onChange={e => setSearch(e.target.value)}/><kbd>⌘ K</kbd></div>
          <button className="aur-icon-btn" aria-label="Notifications"><Bell size={17}/><i/></button>
          <div className="aur-top-avatar">M</div>
        </div>
      </header>

      <div className="aur-content">
        <div className="aur-demo-banner"><span className="aur-demo-dot"/> DEMO ENVIRONMENT <span className="aur-banner-divider"/> All figures are illustrative and use synthetic data.</div>
        <div className="aur-page-heading">
          <div><div className="aur-eyebrow">THURSDAY, NOVEMBER 19, 2026</div><h1>{page === 'Overview' ? 'Your wealth, in perspective.' : page}</h1><p>{page === 'Overview' ? 'A considered view of your portfolio, performance and financial position.' : page === 'Portfolio' ? 'Explore your illustrative holdings and asset allocation.' : page === 'Activity' ? 'A transparent record of portfolio activity and events.' : 'A workspace for market context, research and informed decisions.'}</p></div>
          <div className="aur-heading-actions"><button className="aur-button aur-button-quiet" onClick={() => window.print()}><Download size={15}/> Export view</button><button className="aur-button aur-button-primary" onClick={() => setPage('Research')}><Sparkles size={15}/> Explore insights</button></div>
        </div>

        {page === 'Overview' && <>
          <section className="aur-metrics">
            <Metric label="TOTAL PORTFOLIO VALUE" value="$128,450.20" note="+$9,982.40 this year" icon={Wallet} accent="lavender" trend="+8.42%"/>
            <Metric label="INVESTED CAPITAL" value="$108,000.00" note="Across 5 positions" icon={BriefcaseBusiness} accent="sage" trend="84.1% invested"/>
            <Metric label="AVAILABLE CASH" value="$20,450.20" note="Across 1 cash account" icon={Landmark} accent="gold" trend="15.9% cash"/>
            <Metric label="TOTAL RETURN" value="+$9,982.40" note="Time-weighted · 1 year" icon={Activity} accent="blue" trend="+8.42%"/>
          </section>
          <section className="aur-overview-grid">
            <div className="aur-panel aur-performance">
              <div className="aur-panel-head"><div><div className="aur-section-kicker">PERFORMANCE</div><h2>Portfolio value</h2><p>Illustrative portfolio history · USD</p></div><div className="aur-range">{ranges.map(r => <button key={r} onClick={() => setRange(r)} className={range === r ? 'selected' : ''}>{r}</button>)}</div></div>
              <div className="aur-chart-summary"><strong>$128,450.20</strong><span className="aur-positive"><ArrowUpRight size={15}/> 8.42%</span><span className="aur-chart-caption">over the selected period</span></div>
              <div className="aur-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData} margin={{top:10,right:8,left:-18,bottom:0}}><defs><linearGradient id="aurFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#b7a4ff" stopOpacity={0.23}/><stop offset="100%" stopColor="#b7a4ff" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#29312f" vertical={false}/><XAxis dataKey="label" tick={{fill:'#77837d',fontSize:11}} axisLine={false} tickLine={false}/><YAxis domain={['dataMin - 5','dataMax + 5']} tick={{fill:'#77837d',fontSize:10}} axisLine={false} tickLine={false} tickFormatter={v => '$'+Math.round(v)+'k'}/><Tooltip contentStyle={{background:'#17201d',border:'1px solid #34413b',borderRadius:10,color:'#f2f3ed'}} formatter={v => [fmt(v*1000),'Portfolio value']}/><Area type="monotone" dataKey="value" stroke="#b7a4ff" strokeWidth={2.4} fill="url(#aurFill)" activeDot={{r:4,fill:'#d8ceff',stroke:'#17201d',strokeWidth:2}}/></AreaChart></ResponsiveContainer></div>
              <div className="aur-chart-foot"><span><i className="aur-legend-dot"/> Portfolio value</span><span>Illustrative historical series</span></div>
            </div>
            <div className="aur-panel aur-allocation">
              <div className="aur-panel-head"><div><div className="aur-section-kicker">ALLOCATION</div><h2>Asset mix</h2><p>By current market value</p></div><button className="aur-more" aria-label="More allocation options"><Ellipsis size={19}/></button></div>
              <div className="aur-donut-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={allocation} dataKey="value" nameKey="name" innerRadius={69} outerRadius={91} paddingAngle={3} stroke="none">{allocation.map(item => <Cell key={item.name} fill={item.color}/>)}</Pie><Tooltip formatter={(v) => [v+'%','Allocation']} contentStyle={{background:'#17201d',border:'1px solid #34413b',borderRadius:10,color:'#f2f3ed'}}/></PieChart></ResponsiveContainer><div className="aur-donut-center"><strong>4</strong><span>ASSET CLASSES</span></div></div>
              <div className="aur-allocation-list">{allocation.map(item => <div className="aur-allocation-row" key={item.name}><span className="aur-allocation-name"><i style={{background:item.color}}/>{item.name}</span><strong>{item.value}%</strong><span>{fmt(item.amount)}</span></div>)}</div>
            </div>
          </section>
          <section className="aur-bottom-grid">
            <HoldingsTable holdings={holdings.slice(0,4)} onView={() => setPage('Portfolio')}/>
            <ActivityPanel onView={() => setPage('Activity')}/>
          </section>
        </>}

        {page === 'Portfolio' && <section className="aur-panel aur-full-panel"><div className="aur-panel-head"><div><div className="aur-section-kicker">YOUR POSITIONS</div><h2>Holdings</h2><p>5 illustrative positions · USD reporting currency</p></div><div className="aur-table-total"><span>TOTAL VALUE</span><strong>$111,040.20</strong></div></div><HoldingsTable holdings={visibleHoldings} full/></section>}

        {page === 'Activity' && <section className="aur-panel aur-full-panel"><div className="aur-panel-head"><div><div className="aur-section-kicker">PORTFOLIO HISTORY</div><h2>Recent activity</h2><p>Illustrative events and account movements</p></div></div><ActivityPanel full/></section>}

        {page === 'Research' && <section className="aur-research-grid"><div className="aur-panel aur-research-card"><div className="aur-research-icon"><Sparkles size={19}/></div><div className="aur-section-kicker">PORTFOLIO NOTE · DEMO</div><h2>Consistency over prediction.</h2><p>A durable investment process is built around clear objectives, diversification, costs and risk controls — not confident guesses about tomorrow.</p><div className="aur-note-tags"><span>Long-term thinking</span><span>Risk awareness</span><span>Evidence first</span></div></div><div className="aur-panel aur-watchlist"><div className="aur-panel-head"><div><div className="aur-section-kicker">WATCHLIST</div><h2>Market reference</h2><p>Illustrative reference list · not live quotes</p></div></div>{[['SPY','S&P 500 ETF','Equity benchmark'],['AGG','US Aggregate Bond','Fixed income'],['GLD','Gold ETF','Alternative asset'],['BTC','Bitcoin','Digital asset']].map((item,i)=><div className="aur-watch-row" key={item[0]}><div className="aur-watch-symbol">{item[0].slice(0,1)}</div><div><strong>{item[0]}</strong><span>{item[1]}</span></div><small>{item[2]}</small><span className="aur-watch-status">Reference</span></div>)}</div></section>}
        <footer className="aur-footer"><span>© 2026 AURELIUS · PORTFOLIO INTELLIGENCE</span><span><ShieldCheck size={13}/> Demo mode · No live financial connections</span></footer>
      </div>
    </main>
  </div>
}

function Metric({label,value,note,icon:Icon,accent,trend}) {
  return <div className="aur-metric"><div className="aur-metric-top"><span>{label}</span><i className={'aur-metric-icon '+accent}><Icon size={17}/></i></div><strong>{value}</strong><div className="aur-metric-bottom"><span>{note}</span><em>{trend}</em></div></div>
}

function HoldingsTable({holdings,onView,full=false}) {
  return <div className={'aur-panel aur-holdings '+(full?'aur-table-panel':'')}>
    <div className="aur-panel-head"><div><div className="aur-section-kicker">PORTFOLIO</div><h2>{full?'All holdings':'Top holdings'}</h2><p>{full?'Position-level view of the demo portfolio':'Your largest positions by market value'}</p></div>{!full && <button className="aur-text-link" onClick={onView}>View portfolio <ArrowUpRight size={14}/></button>}</div>
    <div className="aur-table-scroll"><table className="aur-table"><thead><tr><th>ASSET</th><th>UNITS</th><th>PRICE</th><th>MARKET VALUE</th><th>DAY CHANGE</th>{full && <th>WEIGHT</th>}</tr></thead><tbody>{holdings.map(h=><tr key={h.symbol}><td><div className="aur-asset-cell"><div className="aur-asset-logo">{h.symbol.slice(0,1)}</div><div><strong>{h.symbol}</strong><span>{h.name}</span></div></div></td><td>{h.units}</td><td>{h.price}</td><td className="aur-value-cell">{h.value}</td><td><span className={h.positive?'aur-positive':'aur-negative'}>{h.change}</span></td>{full && <td>{h.weight.toFixed(1)}%</td>}</tr>)}</tbody></table>{holdings.length===0 && <div className="aur-empty">No matching holdings. Try another search.</div>}</div>
  </div>
}

function ActivityPanel({onView,full=false}) {
  return <div className={'aur-panel aur-activity '+(full?'aur-activity-full':'')}><div className="aur-panel-head"><div><div className="aur-section-kicker">LATEST UPDATES</div><h2>{full?'Activity log':'Recent activity'}</h2><p>Latest events in this demo workspace</p></div>{!full && <button className="aur-text-link" onClick={onView}>View all <ArrowUpRight size={14}/></button>}</div><div className="aur-activity-list">{activity.map((item,i)=><div className="aur-activity-row" key={item.title}><div className={'aur-activity-icon '+(item.positive?'positive':'neutral')}><item.icon size={16}/></div><div className="aur-activity-copy"><strong>{item.title}</strong><span>{item.detail}</span></div><div className={'aur-activity-amount '+(item.positive?'aur-positive':'')}>{item.amount}</div></div>)}</div></div>
}

export default App
