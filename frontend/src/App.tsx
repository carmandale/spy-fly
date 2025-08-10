// import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
// import Dashboard from './components/Dashboard'
// import ExecutionPage from './pages/ExecutionPage'

function App() {
  console.log('App component is rendering')
  
  // Test if React is working
  return (
    <div style={{ backgroundColor: '#1a1a1a', color: 'white', padding: '20px', minHeight: '100vh' }}>
      <h1>SPY-FLY Dashboard</h1>
      <p>Testing: React is working!</p>
      <p>Now let's try to load the Dashboard component...</p>
      <button 
        onClick={() => {
          console.log('Button clicked - trying to load Dashboard')
          // Dynamic import to see the error
          import('./components/Dashboard').then(module => {
            console.log('Dashboard module loaded:', module)
          }).catch(err => {
            console.error('Error loading Dashboard:', err)
            alert('Error loading Dashboard: ' + err.message)
          })
        }}
        style={{ padding: '10px', marginTop: '20px' }}
      >
        Click to Load Dashboard (check console)
      </button>
    </div>
  )
}

export default App
