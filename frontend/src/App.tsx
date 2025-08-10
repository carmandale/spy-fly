// import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
// import ExecutionPage from './pages/ExecutionPage'

function App() {
  console.log('App component is rendering')
  try {
    return <Dashboard />
  } catch (error) {
    console.error('Error rendering Dashboard:', error)
    return (
      <div style={{ padding: '20px', color: 'red' }}>
        <h1>Error loading Dashboard</h1>
        <pre>{String(error)}</pre>
      </div>
    )
  }
}

export default App
