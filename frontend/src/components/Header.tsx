import { Menu } from 'lucide-react'
import ConnectionStatus from './ConnectionStatus'

export default function Header() {
  return (
    <header className="h-16 bg-slate-950 border-b border-slate-800 flex items-center justify-between px-4 md:px-6">
      <div className="flex items-center md:hidden">
        <button className="text-slate-300 hover:text-white p-2">
          <Menu className="w-6 h-6" />
        </button>
        <span className="font-bold text-lg text-slate-100 ml-3">JalMarg</span>
      </div>
      <div className="hidden md:block">
        <h2 className="text-xl font-semibold text-slate-200">Dashboard Overview</h2>
      </div>
      <div className="flex items-center">
        <ConnectionStatus />
      </div>
    </header>
  )
}
