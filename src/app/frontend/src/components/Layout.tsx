// src/app/frontend/src/components/Layout.tsx
import { Box, Flex } from '@chakra-ui/react'
import Navigation from './Navigation'
import { useLocation } from 'react-router-dom'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const isAuthPage = location.pathname === '/login' || location.pathname === '/signup'

  return (
    <Flex h="100vh" flexDirection="column">
      {!isAuthPage && <Navigation />}
      <Box flex={1} overflowY="auto">
        {children}
      </Box>
    </Flex>
  )
}
