export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen-dynamic min-h-screen-dynamic flex flex-col bg-cyber-dark overflow-hidden no-select">
      <div className="flex-1 flex flex-col max-w-md mx-auto w-full">
        {children}
      </div>
    </div>
  )
}
