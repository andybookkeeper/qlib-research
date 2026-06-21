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
import { Link as RouterLink, Navigate, useNavigate } from 'react-router-dom'
import { apiClient } from '../api/client'
import { useAuth } from '../auth/AuthContext'

const Signup: React.FC = () => {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const toast = useToast()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async () => {
    try {
      setLoading(true)
      await apiClient.auth.signup({
        username,
        email,
        password,
        full_name: fullName || undefined,
      })
      toast({
        title: 'Account created',
        description: 'You can now sign in with your credentials.',
        status: 'success',
      })
      navigate('/login', { replace: true })
    } catch (err) {
      toast({
        title: 'Signup failed',
        description: err instanceof Error ? err.message : 'Unable to create account',
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
          <Heading size="lg">Create account</Heading>
          <Text color="gray.600" mt={2}>
            Set up your trading profile
          </Text>
        </CardHeader>
        <CardBody>
          <Box display="grid" gap={4}>
            <FormControl>
              <FormLabel>Username</FormLabel>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} />
            </FormControl>
            <FormControl>
              <FormLabel>Email</FormLabel>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} />
            </FormControl>
            <FormControl>
              <FormLabel>Full name (optional)</FormLabel>
              <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
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
              isDisabled={!username || !email || !password}
            >
              Create account
            </Button>
            <Text fontSize="sm">
              Already have an account?{' '}
              <Link as={RouterLink} to="/login" color="blue.500">
                Sign in
              </Link>
            </Text>
          </Box>
        </CardBody>
      </Card>
    </Container>
  )
}

export default Signup

