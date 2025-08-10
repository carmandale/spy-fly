import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import ExecutionPage from './pages/ExecutionPage'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/execute/:recommendationId" element={<ExecutionPage />} />
      </Routes>
    </Router>
  )
  // return (
  //   <Router>
  //     <Routes>
  //       <Route path="/" element={<Dashboard />} />
  //       <Route path="/execute/:recommendationId" element={<ExecutionPage />} />
  //     </Routes>
  //   </Router>
  // )
}

export default App
