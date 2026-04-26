import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import Home from './pages/Home'
import Analyze from './pages/Analyze'
import History from './pages/History'
import Result from './pages/Result'
import Analytics from './pages/Analytics'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/analyze/:jobId" element={<Analyze />} />
          <Route path="/history" element={<History />} />
          <Route path="/result/:jobId" element={<Result />} />
          <Route path="/analytics" element={<Analytics />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App
