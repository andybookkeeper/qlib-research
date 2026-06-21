// src/app/frontend/src/components/Navigation.tsx
import { HStack, Button, Box, Heading } from '@chakra-ui/react'
import { Link as RouterLink, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Navigation() {
  const location = useLocation()
  const { user, logout } = useAuth()

  const isActive = (path: string) => location.pathname === path

  return (
    <Box bg="blue.600" color="white" p={4} shadow="md">
      <HStack spacing={0} justify="space-between" align="center">
        <Heading size="md" ml={4}>
          📊 Qlib Trading Platform
        </Heading>
        <HStack spacing={0}>
          <RouterLink to="/">
            <Button
              variant={isActive('/') ? 'solid' : 'ghost'}
              bg={isActive('/') ? 'blue.800' : 'transparent'}
              _hover={{ bg: 'blue.700' }}
            >
              Dashboard
            </Button>
          </RouterLink>
          <RouterLink to="/trading">
            <Button
              variant={isActive('/trading') ? 'solid' : 'ghost'}
              bg={isActive('/trading') ? 'blue.800' : 'transparent'}
              _hover={{ bg: 'blue.700' }}
            >
              Trading
            </Button>
          </RouterLink>
          <RouterLink to="/portfolio">
            <Button
              variant={isActive('/portfolio') ? 'solid' : 'ghost'}
              bg={isActive('/portfolio') ? 'blue.800' : 'transparent'}
              _hover={{ bg: 'blue.700' }}
            >
              Portfolio
            </Button>
          </RouterLink>
          <RouterLink to="/research">
            <Button
              variant={isActive('/research') ? 'solid' : 'ghost'}
              bg={isActive('/research') ? 'blue.800' : 'transparent'}
              _hover={{ bg: 'blue.700' }}
            >
              Research
            </Button>
          </RouterLink>
          <Button variant="ghost" _hover={{ bg: 'blue.700' }} onClick={logout}>
            Logout {user?.username ? `(${user.username})` : ''}
          </Button>
        </HStack>
      </HStack>
    </Box>
  )
}
