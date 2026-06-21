// src/app/frontend/src/components/Layout.tsx
import { Box, Flex } from '@chakra-ui/react'
import Navigation from './Navigation'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <Flex h="100vh" flexDirection="column">
      <Navigation />
      <Box flex={1} overflowY="auto">
        {children}
      </Box>
    </Flex>
  )
}
