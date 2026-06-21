import React, { useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Container,
  FormControl,
  FormLabel,
  Heading,
  Input,
  Link,
  Text,
  useToast,
} from '@chakra-ui/react'
import { Link as RouterLink, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { apiClient } from '../api/client'
import { useAuth } from '../auth/AuthContext'

const Login: React.FC = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, isAuthenticated } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/'

  if (isAuthenticated) {
    return <Navigate to={from} replace />
  }

  const handleSubmit = async () => {
    try {
      setLoading(true)
      const response = await apiClient.auth.login(username, password)
      await login(response.access_token)
      navigate(from, { replace: true })
    } catch (err) {
      toast({
        title: 'Login failed',
        description: err instanceof Error ? err.message : 'Invalid username or password',
        status: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxW="md" py={16}>
      <Card>
        <CardHeader>
          <Heading size="lg">Sign in</Heading>
          <Text color="gray.600" mt={2}>
            Access your trading workspace
          </Text>
        </CardHeader>
        <CardBody>
          <Box display="grid" gap={4}>
            <FormControl>
              <FormLabel>Username</FormLabel>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} />
            </FormControl>
            <FormControl>
              <FormLabel>Password</FormLabel>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </FormControl>
            <Button
              colorScheme="blue"
              onClick={handleSubmit}
              isLoading={loading}
              isDisabled={!username || !password}
            >
              Sign in
            </Button>
            <Text fontSize="sm">
              New here?{' '}
              <Link as={RouterLink} to="/signup" color="blue.500">
                Create an account
              </Link>
            </Text>
          </Box>
        </CardBody>
      </Card>
    </Container>
  )
}

export default Login

