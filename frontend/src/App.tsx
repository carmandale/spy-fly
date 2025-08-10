// import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
// import ExecutionPage from './pages/ExecutionPage'

function App() {
  console.log('App component rendering')
  return (
    <div style={{ backgroundColor: 'black', color: 'white', padding: '20px', minHeight: '100vh' }}>
      <h1>SPY-FLY Dashboard Loading...</h1>
      <Dashboard />
    </div>
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
