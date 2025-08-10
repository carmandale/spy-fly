import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import ExecutionPage from './pages/ExecutionPage'

function App() {
  // Use base URL from environment for GitHub Pages compatibility
  const basename = import.meta.env.BASE_URL || '/'
  
  return (
    <Router basename={basename}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/execution" element={<ExecutionPage />} />
      </Routes>
    </Router>
  )
}

export default App
