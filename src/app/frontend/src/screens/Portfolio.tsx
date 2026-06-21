import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Container,
  Flex,
  FormControl,
  FormLabel,
  Grid,
  Heading,
  HStack,
  Select,
  Spinner,
  Stat,
  StatArrow,
  StatHelpText,
  StatLabel,
  StatNumber,
  Tab,
  Table,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  useToast,
} from '@chakra-ui/react'
import { useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, LineChart, Line } from 'recharts'

import { PortfolioOverview } from '../types'
import { apiClient } from '../api/client'

type PortfolioPerformance = {
  cumulative_returns: number
  volatility: number
  risk_free_rate: number
}

type BrokerPosition = {
  ticker: string
  quantity: number
  entry_price: number
  current_price: number
  cost_basis: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
}

type BrokerTrade = {
  trade_id: string
  ticker: string
  side: string
  entry_date: string
  exit_date: string
  realized_pnl: number
  realized_pnl_pct: number
  holding_days: number
}

const COLORS = ['#2B6CB0', '#38A169', '#D69E2E', '#805AD5', '#DD6B20', '#319795', '#E53E3E']

const formatCurrency = (value: number): string =>
  `$${Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '0.00'}`

const Portfolio: React.FC = () => {
  const [overview, setOverview] = useState<PortfolioOverview | null>(null)
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null)
  const [positions, setPositions] = useState<BrokerPosition[]>([])
  const [trades, setTrades] = useState<BrokerTrade[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [positionFilter, setPositionFilter] = useState<'all' | 'winners' | 'losers'>('all')
  const toast = useToast()
  const navigate = useNavigate()

  const fetchData = async (showSpinner = false) => {
    try {
      setErrorMessage(null)
      if (showSpinner) {
        setLoading(true)
      } else {
        setUpdating(true)
      }
      const ov = (await apiClient.portfolio.getOverview()) as PortfolioOverview
      const [perfResult, posResult, tradeResult] = await Promise.allSettled([
        apiClient.portfolio.getPerformance() as Promise<PortfolioPerformance>,
        apiClient.broker.getPositions() as Promise<BrokerPosition[]>,
        apiClient.broker.getTrades() as Promise<BrokerTrade[]>,
      ])

      setOverview(ov)
      setPerformance(perfResult.status === 'fulfilled' ? perfResult.value : null)
      setPositions(posResult.status === 'fulfilled' ? posResult.value : [])
      setTrades(tradeResult.status === 'fulfilled' ? tradeResult.value : [])
      setLastUpdated(new Date().toLocaleTimeString())

      const partialErrors: string[] = []
      if (perfResult.status === 'rejected') partialErrors.push('performance')
      if (posResult.status === 'rejected') partialErrors.push('positions')
      if (tradeResult.status === 'rejected') partialErrors.push('trades')
      if (partialErrors.length > 0) {
        setErrorMessage(`Some analytics sections are unavailable: ${partialErrors.join(', ')}.`)
      }
    } catch {
      setOverview(null)
      setPerformance(null)
      setPositions([])
      setTrades([])
      setErrorMessage('Unable to load portfolio overview. Please refresh and try again.')
      toast({ title: 'Error loading portfolio analytics', status: 'error' })
    } finally {
      setLoading(false)
      setUpdating(false)
    }
  }

  useEffect(() => {
    fetchData(true)
    const interval = setInterval(() => fetchData(false), 15000)
    return () => clearInterval(interval)
  }, [])

  const filteredPositions = useMemo(() => {
    if (positionFilter === 'winners') return positions.filter((p) => p.unrealized_pnl >= 0)
    if (positionFilter === 'losers') return positions.filter((p) => p.unrealized_pnl < 0)
    return positions
  }, [positions, positionFilter])

  const allocationData = useMemo(() => {
    if (!overview) return []
    const positionAllocations = positions
      .filter((p) => Math.abs(p.market_value) > 0)
      .map((p) => ({ name: p.ticker, value: Math.abs(p.market_value) }))
    return [...positionAllocations, { name: 'Cash', value: Math.max(overview.cash, 0) }]
  }, [overview, positions])

  const pnlByTicker = useMemo(
    () =>
      positions
        .map((p) => ({ ticker: p.ticker, pnl: p.unrealized_pnl }))
        .sort((a, b) => Math.abs(b.pnl) - Math.abs(a.pnl))
        .slice(0, 10),
    [positions]
  )

  const cumulativePnlSeries = useMemo(() => {
    const chronological = [...trades]
      .filter((t) => t.exit_date)
      .sort((a, b) => new Date(a.exit_date).getTime() - new Date(b.exit_date).getTime())
    let cumulative = 0
    return chronological.map((t) => {
      cumulative += t.realized_pnl || 0
      return {
        time: new Date(t.exit_date).toLocaleDateString(),
        cumulative_pnl: Number(cumulative.toFixed(2)),
      }
    })
  }, [trades])

  if (loading && !overview) {
    return (
      <Container py={8}>
        <Flex justify="center" align="center" h="400px">
          <Spinner size="xl" />
        </Flex>
      </Container>
    )
  }

  if (!overview) {
    return (
      <Container py={8}>
        <Alert status="error" mb={4}>
          <AlertIcon />
          Unable to load portfolio data.
        </Alert>
        <Button onClick={() => fetchData(true)}>Retry</Button>
      </Container>
    )
  }

  const isPositive = overview.total_pnl >= 0

  return (
    <Container maxW="100%" py={8} px={6}>
      <Flex justify="space-between" align="center" mb={8} wrap="wrap" gap={3}>
        <Box>
          <Heading size="lg">Portfolio Analytics</Heading>
          <Text color="gray.600">Last updated: {lastUpdated || 'n/a'}</Text>
        </Box>
        <HStack>
          <Button variant="outline" onClick={() => fetchData(false)} isLoading={updating}>
            Refresh
          </Button>
          <Button colorScheme="blue" onClick={() => navigate('/trading')}>
            Go to Trading
          </Button>
        </HStack>
      </Flex>

      {errorMessage && (
        <Alert status="warning" mb={6}>
          <AlertIcon />
          {errorMessage}
        </Alert>
      )}

      <Grid templateColumns="repeat(auto-fit, minmax(230px, 1fr))" gap={6} mb={8}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Portfolio Value</StatLabel>
              <StatNumber>{formatCurrency(overview.portfolio_value)}</StatNumber>
              <StatHelpText>Cash: {formatCurrency(overview.cash)}</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total P&L</StatLabel>
              <StatNumber color={isPositive ? 'green.600' : 'red.600'}>{formatCurrency(overview.total_pnl)}</StatNumber>
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
              <StatLabel>Realized / Unrealized</StatLabel>
              <StatNumber>{formatCurrency(overview.realized_pnl)}</StatNumber>
              <StatHelpText>Unrealized: {formatCurrency(overview.unrealized_pnl)}</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Open Positions</StatLabel>
              <StatNumber>{overview.open_positions}</StatNumber>
              <StatHelpText>Total trades: {overview.total_trades}</StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Cumulative Return</StatLabel>
              <StatNumber color={(performance?.cumulative_returns || 0) >= 0 ? 'green.600' : 'red.600'}>
                {((performance?.cumulative_returns || 0) * 100).toFixed(2)}%
              </StatNumber>
              <StatHelpText>Volatility: {((performance?.volatility || 0) * 100).toFixed(2)}%</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </Grid>

      <Tabs colorScheme="blue" variant="enclosed">
        <TabList>
          <Tab>Allocation & Exposure</Tab>
          <Tab>Position Analytics</Tab>
          <Tab>Trade Journal</Tab>
        </TabList>

        <TabPanels>
          <TabPanel px={0} pt={6}>
            <Grid templateColumns={{ base: '1fr', xl: '1fr 1fr' }} gap={6}>
              <Card>
                <CardHeader>
                  <Heading size="md">Allocation Mix</Heading>
                </CardHeader>
                <CardBody h="320px">
                  {allocationData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={allocationData} dataKey="value" nameKey="name" outerRadius={110} label>
                          {allocationData.map((entry, index) => (
                            <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <Alert status="info">
                      <AlertIcon />
                      No allocation data yet.
                    </Alert>
                  )}
                </CardBody>
              </Card>

              <Card>
                <CardHeader>
                  <Heading size="md">Exposure Snapshot</Heading>
                </CardHeader>
                <CardBody>
                  <Grid templateColumns="repeat(2, minmax(0,1fr))" gap={5}>
                    <Box>
                      <Text color="gray.500" fontSize="sm">Gross Exposure</Text>
                      <Heading size="md">{formatCurrency(overview.gross_value)}</Heading>
                    </Box>
                    <Box>
                      <Text color="gray.500" fontSize="sm">Net Exposure</Text>
                      <Heading size="md">{formatCurrency(overview.net_value)}</Heading>
                    </Box>
                    <Box>
                      <Text color="gray.500" fontSize="sm">Invested Ratio</Text>
                      <Heading size="md">
                        {overview.portfolio_value > 0
                          ? ((overview.gross_value / overview.portfolio_value) * 100).toFixed(1)
                          : '0.0'}
                        %
                      </Heading>
                    </Box>
                    <Box>
                      <Text color="gray.500" fontSize="sm">Risk-free rate</Text>
                      <Heading size="md">{((performance?.risk_free_rate || 0) * 100).toFixed(2)}%</Heading>
                    </Box>
                  </Grid>
                </CardBody>
              </Card>
            </Grid>
          </TabPanel>

          <TabPanel px={0} pt={6}>
            <Card mb={6}>
              <CardHeader>
                <Flex justify="space-between" align="center" wrap="wrap" gap={3}>
                  <Heading size="md">Unrealized P&L by Ticker</Heading>
                  <FormControl w="220px">
                    <FormLabel mb={1}>Position Filter</FormLabel>
                    <Select value={positionFilter} onChange={(e) => setPositionFilter(e.target.value as 'all' | 'winners' | 'losers')}>
                      <option value="all">All Positions</option>
                      <option value="winners">Winners Only</option>
                      <option value="losers">Losers Only</option>
                    </Select>
                  </FormControl>
                </Flex>
              </CardHeader>
              <CardBody h="320px">
                {pnlByTicker.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={pnlByTicker}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="ticker" />
                      <YAxis />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Bar dataKey="pnl" fill="#3182CE" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <Alert status="info">
                    <AlertIcon />
                    No position P&L data available.
                  </Alert>
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader>
                <Heading size="md">Detailed Positions ({filteredPositions.length})</Heading>
              </CardHeader>
              <CardBody>
                {filteredPositions.length > 0 ? (
                  <Table size="sm">
                    <Thead>
                      <Tr>
                        <Th>Ticker</Th>
                        <Th isNumeric>Qty</Th>
                        <Th isNumeric>Entry</Th>
                        <Th isNumeric>Current</Th>
                        <Th isNumeric>Market Value</Th>
                        <Th isNumeric>Unrealized P&L</Th>
                        <Th isNumeric>P&L %</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {filteredPositions.map((position) => (
                        <Tr key={position.ticker}>
                          <Td fontWeight="bold">{position.ticker}</Td>
                          <Td isNumeric>{position.quantity}</Td>
                          <Td isNumeric>{formatCurrency(position.entry_price)}</Td>
                          <Td isNumeric>{formatCurrency(position.current_price)}</Td>
                          <Td isNumeric>{formatCurrency(position.market_value)}</Td>
                          <Td isNumeric color={position.unrealized_pnl >= 0 ? 'green.600' : 'red.600'}>
                            {formatCurrency(position.unrealized_pnl)}
                          </Td>
                          <Td isNumeric color={position.unrealized_pnl_pct >= 0 ? 'green.600' : 'red.600'}>
                            {position.unrealized_pnl_pct.toFixed(2)}%
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                ) : (
                  <Text color="gray.500">No positions match the selected filter.</Text>
                )}
              </CardBody>
            </Card>
          </TabPanel>

          <TabPanel px={0} pt={6}>
            <Card mb={6}>
              <CardHeader>
                <Heading size="md">Cumulative Realized P&L</Heading>
              </CardHeader>
              <CardBody h="320px">
                {cumulativePnlSeries.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={cumulativePnlSeries}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Line type="monotone" dataKey="cumulative_pnl" stroke="#2B6CB0" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <Alert status="info">
                    <AlertIcon />
                    Closed trades will appear here once available.
                  </Alert>
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader>
                <Heading size="md">Recent Closed Trades ({trades.length})</Heading>
              </CardHeader>
              <CardBody>
                {trades.length > 0 ? (
                  <Table size="sm">
                    <Thead>
                      <Tr>
                        <Th>Ticker</Th>
                        <Th>Side</Th>
                        <Th>Exit Time</Th>
                        <Th isNumeric>Realized P&L</Th>
                        <Th isNumeric>P&L %</Th>
                        <Th isNumeric>Holding Days</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {trades.slice(0, 25).map((trade) => (
                        <Tr key={trade.trade_id}>
                          <Td fontWeight="bold">{trade.ticker}</Td>
                          <Td>
                            <Badge colorScheme={trade.side.toLowerCase() === 'buy' ? 'green' : 'red'}>
                              {trade.side.toUpperCase()}
                            </Badge>
                          </Td>
                          <Td>{new Date(trade.exit_date).toLocaleString()}</Td>
                          <Td isNumeric color={trade.realized_pnl >= 0 ? 'green.600' : 'red.600'}>
                            {formatCurrency(trade.realized_pnl)}
                          </Td>
                          <Td isNumeric color={trade.realized_pnl_pct >= 0 ? 'green.600' : 'red.600'}>
                            {trade.realized_pnl_pct.toFixed(2)}%
                          </Td>
                          <Td isNumeric>{trade.holding_days}</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                ) : (
                  <Text color="gray.500">No closed trades yet.</Text>
                )}
              </CardBody>
            </Card>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Container>
  )
}

export default Portfolio
