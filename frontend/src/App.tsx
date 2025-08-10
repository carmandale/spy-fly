// import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
// import ExecutionPage from './pages/ExecutionPage'

function App() {
  console.log('App component rendering')
  return <Dashboard />
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
