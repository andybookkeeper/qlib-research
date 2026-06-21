// src/app/frontend/src/screens/Dashboard.tsx
import React, { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Grid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Alert,
  AlertIcon,
  Flex,
} from '@chakra-ui/react'
import { DashboardData, Position } from '../types'
import { apiClient } from '../api/client'

const Dashboard: React.FC = () => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setLoading(true)
        const data = await apiClient.portfolio.getDashboard()
        setDashboard(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch dashboard')
      } finally {
        setLoading(false)
      }
    }

    fetchDashboard()
    // Refresh every 5 seconds
    const interval = setInterval(fetchDashboard, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading && !dashboard) {
    return (
      <Container py={8}>
        <Flex justify="center" align="center" h="400px">
          <Spinner size="xl" />
        </Flex>
      </Container>
    )
  }

  if (error) {
    return (
      <Container py={8}>
        <Alert status="error">
          <AlertIcon />
          {error}
        </Alert>
      </Container>
    )
  }

  if (!dashboard) return null

  const isPositive = dashboard.total_pnl >= 0

  return (
    <Container maxW="100%" py={8} px={6}>
      <Heading mb={8} size="lg">
        Portfolio Dashboard
      </Heading>

      {/* Key Metrics */}
      <Grid templateColumns="repeat(auto-fit, minmax(250px, 1fr))" gap={6} mb={8}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Portfolio Value</StatLabel>
              <StatNumber>${dashboard.portfolio_value.toLocaleString()}</StatNumber>
              <StatHelpText>
                <StatArrow type={isPositive ? 'increase' : 'decrease'} />
                {Math.abs(dashboard.total_pnl_pct).toFixed(2)}%
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total P&L</StatLabel>
              <StatNumber color={isPositive ? 'green.600' : 'red.600'}>
                ${dashboard.total_pnl.toLocaleString()}
              </StatNumber>
              <StatHelpText>
                Realized: ${dashboard.realized_pnl.toLocaleString()}
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Cash Available</StatLabel>
              <StatNumber>${dashboard.cash.toLocaleString()}</StatNumber>
              <StatHelpText>
                {((dashboard.cash / dashboard.portfolio_value) * 100).toFixed(1)}% of portfolio
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Sharpe Ratio</StatLabel>
              <StatNumber>{dashboard.sharpe_ratio.toFixed(2)}</StatNumber>
              <StatHelpText>Risk-adjusted returns</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Max Drawdown</StatLabel>
              <StatNumber color="red.600">
                {(dashboard.max_drawdown * 100).toFixed(1)}%
              </StatNumber>
              <StatHelpText>Peak to trough decline</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Value at Risk (95%)</StatLabel>
              <StatNumber>${dashboard.var_95.toLocaleString()}</StatNumber>
              <StatHelpText>Potential max loss</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </Grid>

      {/* Risk Warnings */}
      {dashboard.risk_warnings && dashboard.risk_warnings.length > 0 && (
        <Box mb={8}>
          {dashboard.risk_warnings.map((warning, idx) => (
            <Alert key={idx} status="warning" mb={2}>
              <AlertIcon />
              {warning}
            </Alert>
          ))}
        </Box>
      )}

      {/* Positions */}
      <Card>
        <CardHeader>
          <Heading size="md">Open Positions ({dashboard.open_positions})</Heading>
        </CardHeader>
        <CardBody>
          {dashboard.positions && dashboard.positions.length > 0 ? (
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>Symbol</Th>
                  <Th isNumeric>Qty</Th>
                  <Th isNumeric>Entry</Th>
                  <Th isNumeric>Current</Th>
                  <Th isNumeric>Value</Th>
                  <Th isNumeric>P&L</Th>
                  <Th isNumeric>P&L %</Th>
                </Tr>
              </Thead>
              <Tbody>
                {dashboard.positions.map((pos: Position) => (
                  <Tr key={pos.symbol}>
                    <Td fontWeight="bold">{pos.symbol}</Td>
                    <Td isNumeric>{pos.quantity}</Td>
                    <Td isNumeric>${pos.entry_price.toFixed(2)}</Td>
                    <Td isNumeric>${pos.current_price.toFixed(2)}</Td>
                    <Td isNumeric>${pos.market_value.toLocaleString()}</Td>
                    <Td isNumeric color={pos.pnl >= 0 ? 'green.600' : 'red.600'}>
                      ${pos.pnl.toFixed(2)}
                    </Td>
                    <Td isNumeric color={pos.pnl_pct >= 0 ? 'green.600' : 'red.600'}>
                      {pos.pnl_pct.toFixed(2)}%
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          ) : (
            <Heading size="sm" color="gray.500">
              No open positions
            </Heading>
          )}
        </CardBody>
      </Card>
    </Container>
  )
}

export default Dashboard
