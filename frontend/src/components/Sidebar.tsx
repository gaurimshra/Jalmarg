import Link from 'next/link'
import { Map, AlertTriangle, Route, ShieldAlert, Waves } from 'lucide-react'

export default function Sidebar() {
  const navItems = [
    { name: 'Flood Map', href: '/', icon: Map },
    { name: 'Report Waterlogging', href: '/report', icon: AlertTriangle },
    { name: 'Route Planner', href: '/routes', icon: Route },
    { name: 'Authority Dashboard', href: '/authority', icon: ShieldAlert },
  ];

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 hidden md:flex flex-col">
      <div className="h-16 flex items-center px-6 border-b border-slate-800">
        <Waves className="w-6 h-6 text-teal-400 mr-3" />
        <div className="flex flex-col">
          <span className="font-bold text-lg text-slate-100 tracking-wide leading-tight">JALMARG</span>
          <span className="font-medium text-[10px] text-teal-400 leading-none">जलमार्ग</span>
        </div>
      </div>
      <nav className="flex-1 py-6 px-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <Link 
              key={item.name} 
              href={item.href}
              className="flex items-center px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-teal-400 rounded-lg transition-colors group"
            >
              <Icon className="w-5 h-5 mr-3 group-hover:text-teal-400" />
              <span className="font-medium">{item.name}</span>
            </Link>
          )
        })}
      </nav>
      <div className="p-4 border-t border-slate-800 text-xs text-slate-500">
        <p>JalMarg System v0.1.0</p>
        <p>Phase 1 Foundation</p>
      </div>
    </aside>
  )
}
