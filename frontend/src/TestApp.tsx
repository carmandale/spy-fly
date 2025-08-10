import React from 'react'

function TestApp() {
  console.log('TestApp rendering')
  
  const testImport = async () => {
    console.log('Starting import test...')
    try {
      console.log('Importing Dashboard...')
      const Dashboard = await import('./components/Dashboard')
      console.log('Dashboard imported successfully:', Dashboard)
    } catch (error) {
      console.error('Failed to import Dashboard:', error)
    }
  }
  
  React.useEffect(() => {
    testImport()
  }, [])
  
  return (
    <div style={{ padding: '20px', backgroundColor: '#222', color: 'white', minHeight: '100vh' }}>
      <h1>Test App - Check Console</h1>
      <p>Open browser console to see import errors</p>
    </div>
  )
}

export default TestApp