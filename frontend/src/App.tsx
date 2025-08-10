// import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
// import Dashboard from './components/Dashboard'
// import ExecutionPage from './pages/ExecutionPage'

function App() {
  console.log('App component rendering')
  return (
    <div style={{ backgroundColor: 'black', color: 'white', padding: '20px', minHeight: '100vh' }}>
      <h1>SPY-FLY Dashboard</h1>
      <p>If you see this text, React is working!</p>
      <p>Backend API: http://localhost:8003</p>
      <p>Frontend: http://localhost:3003</p>
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
