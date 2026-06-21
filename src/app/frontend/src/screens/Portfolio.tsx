// src/app/frontend/src/screens/Portfolio.tsx
import React, { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Grid,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Spinner,
  Alert,
  AlertIcon,
  Flex,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Progress,
  useToast,
  FormLabel,
} from '@chakra-ui/react'
import { PortfolioOverview } from '../types'
import { apiClient } from '../api/client'

const Portfolio: React.FC = () => {
  const [overview, setOverview] = useState<PortfolioOverview | null>(null)
  const [performance, setPerformance] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const toast = useToast()

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [ov, perf] = await Promise.all([
          apiClient.portfolio.getOverview(),
          apiClient.portfolio.getPerformance(),
        ])
        setOverview(ov)
        setPerformance(perf)
      } catch (err) {
        toast({ title: 'Error loading portfolio', status: 'error' })
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  if (loading && !overview) {
    return (
      <Container py={8}>
        <Flex justify="center" align="center" h="400px">
          <Spinner size="xl" />
        </Flex>
      </Container>
    )
  }

  if (!overview) return null

  const isPositive = overview.total_pnl >= 0

  return (
    <Container maxW="100%" py={8} px={6}>
      <Heading mb={8} size="lg">
        Portfolio Analysis
      </Heading>

      {/* Summary Stats */}
      <Grid templateColumns="repeat(auto-fit, minmax(250px, 1fr))" gap={6} mb={8}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total Value</StatLabel>
              <StatNumber>${overview.portfolio_value.toLocaleString()}</StatNumber>
              <StatHelpText>
                Cash: ${overview.cash.toLocaleString()}
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Gross Exposure</StatLabel>
              <StatNumber>${overview.gross_value.toLocaleString()}</StatNumber>
              <StatHelpText>
                Net: ${overview.net_value.toLocaleString()}
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total P&L</StatLabel>
              <StatNumber color={isPositive ? 'green.600' : 'red.600'}>
                ${overview.total_pnl.toLocaleString()}
              </StatNumber>
              <StatHelpText>
                <StatArrow type={isPositive ? 'increase' : 'decrease'} />
                {overview.total_pnl_pct.toFixed(2)}%
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Realized P&L</StatLabel>
              <StatNumber>${overview.realized_pnl.toLocaleString()}</StatNumber>
              <StatHelpText>
                Unrealized: ${overview.unrealized_pnl.toLocaleString()}
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Positions</StatLabel>
              <StatNumber>{overview.open_positions}</StatNumber>
              <StatHelpText>
                Total Trades: {overview.total_trades}
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Allocation</StatLabel>
              <StatNumber>
                {((overview.gross_value / overview.portfolio_value) * 100).toFixed(0)}%
              </StatNumber>
              <StatHelpText>
                Invested
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </Grid>

      {/* Performance Chart Section */}
      {performance && (
        <Card mb={8}>
          <CardHeader>
            <Heading size="md">Performance Metrics</Heading>
          </CardHeader>
          <CardBody>
            <Grid templateColumns="repeat(auto-fit, minmax(200px, 1fr))" gap={8}>
              <Box>
                <FormLabel>Cumulative Return</FormLabel>
                <Heading size="lg" color="green.600">
                  {(performance.cumulative_returns * 100).toFixed(2)}%
                </Heading>
                <Progress
                  value={Math.min(
                    Math.abs(performance.cumulative_returns * 100),
                    100
                  )}
                  size="lg"
                  colorScheme={performance.cumulative_returns >= 0 ? 'green' : 'red'}
                  mt={2}
                />
              </Box>
              <Box>
                <FormLabel>Volatility</FormLabel>
                <Heading size="lg">
                  {(performance.volatility * 100).toFixed(2)}%
                </Heading>
                <StatHelpText>Annual volatility</StatHelpText>
              </Box>
              <Box>
                <FormLabel>Risk-Free Rate</FormLabel>
                <Heading size="lg">
                  {(performance.risk_free_rate * 100).toFixed(2)}%
                </Heading>
                <StatHelpText>Benchmark rate</StatHelpText>
              </Box>
            </Grid>
          </CardBody>
        </Card>
      )}

      {/* All Positions */}
      <Card>
        <CardHeader>
          <Heading size="md">
            Position Details ({overview.open_positions} open)
          </Heading>
        </CardHeader>
        <CardBody>
          {overview.open_positions > 0 ? (
            <Alert status="info" mb={4}>
              <AlertIcon />
              Loading position details...
            </Alert>
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

export default Portfolio
