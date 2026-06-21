// src/app/frontend/src/App.tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ChakraProvider } from '@chakra-ui/react'
import Layout from './components/Layout'
import Dashboard from './screens/Dashboard'
import Trading from './screens/Trading'
import Portfolio from './screens/Portfolio'
import Research from './screens/Research'

function App() {
  return (
    <ChakraProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/trading" element={<Trading />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/research" element={<Research />} />
          </Routes>
        </Layout>
      </Router>
    </ChakraProvider>
  )
}

export default App
