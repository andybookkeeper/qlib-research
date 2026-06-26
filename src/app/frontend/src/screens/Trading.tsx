// src/app/frontend/src/screens/Trading.tsx
import React, { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Grid,
  Card,
  CardBody,
  CardHeader,
  Heading,
  FormControl,
  FormLabel,
  Input,
  Select,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Flex,
  Text,
  Tooltip,
  useToast,
} from '@chakra-ui/react'
import { Order, Position } from '../types'
import { apiClient } from '../api/client'

interface OrderForm {
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  price: number
  orderType: 'MARKET' | 'LIMIT' | 'STOP'
}

interface Signal {
  ticker: string
  model_name: string
  signal: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  generated_at: string
}

type BrokerPosition = {
  ticker: string
  quantity: number
  entry_price: number
  current_price: number
  unrealized_pnl_pct?: number
}

type BrokerOrder = {
  order_id: string
  ticker: string
  side: string
  quantity: number
  filled_price?: number | null
  status: string
  created_at: string
}

const Trading: React.FC = () => {
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [tickers, setTickers] = useState<string[]>([])
  const [signals, setSignals] = useState<Signal[]>([])
  const [loadingSignals, setLoadingSignals] = useState(false)
  const [loading, setLoading] = useState(true)
  const [placing, setPlacing] = useState(false)
  const [formData, setFormData] = useState<OrderForm>({
    symbol: '',
    side: 'BUY',
    quantity: 100,
    price: 0,
    orderType: 'MARKET',
  })
  const toast = useToast()

  const fetchSignals = async () => {
    try {
      setLoadingSignals(true)
      const result = await apiClient.research.getSignals()
      setSignals(result.signals || [])
    } catch {
      // ponytail: silent — signals are optional, don't block trading
    } finally {
      setLoadingSignals(false)
    }
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [pos, ord, tick] = await Promise.all([
          apiClient.broker.getPositions(),
          apiClient.broker.getOrders(),
          apiClient.market.getTickers(),
        ])
        setPositions(
          (pos as BrokerPosition[]).map((p) => ({
            symbol: p.ticker,
            quantity: p.quantity,
            entry_price: p.entry_price,
            current_price: p.current_price,
            market_value: p.current_price * p.quantity,
            pnl: ((p.current_price - p.entry_price) * p.quantity),
            pnl_pct: p.unrealized_pnl_pct ?? 0,
          }))
        )
        setOrders(
          (ord as BrokerOrder[]).map((o) => ({
            order_id: o.order_id,
            symbol: o.ticker,
            side: o.side.toUpperCase() as 'BUY' | 'SELL',
            quantity: o.quantity,
            price: o.filled_price ?? 0,
            status: o.status.toUpperCase() as 'PENDING' | 'FILLED' | 'CANCELLED',
            timestamp: o.created_at,
          }))
        )
        setTickers(tick)
        if (!formData.symbol && tick.length > 0) {
          setFormData(prev => ({ ...prev, symbol: tick[0] }))
        }
      } catch (err) {
        toast({ title: 'Error loading data', status: 'error' })
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    fetchSignals()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const handlePlaceOrder = async () => {
    if (!formData.symbol || formData.quantity <= 0) {
      toast({ title: 'Invalid order', status: 'error' })
      return
    }

    try {
      setPlacing(true)
      const order = {
        symbol: formData.symbol,
        side: formData.side,
        quantity: formData.quantity,
        orderType: formData.orderType,
        limitPrice: formData.orderType === 'LIMIT' ? formData.price : undefined,
        stopPrice: formData.orderType === 'STOP' ? formData.price : undefined,
      }
      await apiClient.broker.placeOrder(order)
      
      toast({
        title: `${formData.side} Order Placed`,
        description: `${formData.quantity} shares of ${formData.symbol}`,
        status: 'success',
      })

      // Reset form
      setFormData({
        symbol: formData.symbol,
        side: 'BUY',
        quantity: 100,
        price: 0,
        orderType: 'MARKET',
      })

      // Refresh data
      const [pos, ord] = await Promise.all([
        apiClient.broker.getPositions(),
        apiClient.broker.getOrders(),
      ])
      setPositions(
        (pos as BrokerPosition[]).map((p) => ({
          symbol: p.ticker,
          quantity: p.quantity,
          entry_price: p.entry_price,
          current_price: p.current_price,
          market_value: p.current_price * p.quantity,
          pnl: ((p.current_price - p.entry_price) * p.quantity),
          pnl_pct: p.unrealized_pnl_pct ?? 0,
        }))
      )
      setOrders(
        (ord as BrokerOrder[]).map((o) => ({
          order_id: o.order_id,
          symbol: o.ticker,
          side: o.side.toUpperCase() as 'BUY' | 'SELL',
          quantity: o.quantity,
          price: o.filled_price ?? 0,
          status: o.status.toUpperCase() as 'PENDING' | 'FILLED' | 'CANCELLED',
          timestamp: o.created_at,
        }))
      )
    } catch (err) {
      toast({
        title: 'Order failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        status: 'error',
      })
    } finally {
      setPlacing(false)
    }
  }

  if (loading) {
    return (
      <Container py={8}>
        <Flex justify="center" align="center" h="400px">
          <Spinner size="xl" />
        </Flex>
      </Container>
    )
  }

  return (
    <Container maxW="100%" py={8} px={6}>
      <Heading mb={8} size="lg">
        Trading
      </Heading>

      <Grid templateColumns={{ base: '1fr', lg: '1fr 1fr' }} gap={8} mb={8}>
        {/* Order Form */}
        <Card>
          <CardHeader>
            <Heading size="md">Place Order</Heading>
          </CardHeader>
          <CardBody>
            <Flex direction="column" gap={4}>
              <FormControl>
                <FormLabel>Symbol</FormLabel>
                <Select
                  value={formData.symbol}
                  onChange={(e) =>
                    setFormData({ ...formData, symbol: e.target.value })
                  }
                >
                  {tickers.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Side</FormLabel>
                <Select
                  value={formData.side}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      side: e.target.value as 'BUY' | 'SELL',
                    })
                  }
                >
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Order Type</FormLabel>
                <Select
                  value={formData.orderType}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      orderType: e.target.value as
                        | 'MARKET'
                        | 'LIMIT'
                        | 'STOP',
                    })
                  }
                >
                  <option value="MARKET">MARKET</option>
                  <option value="LIMIT">LIMIT</option>
                  <option value="STOP">STOP</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Quantity</FormLabel>
                <Input
                  type="number"
                  value={formData.quantity}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      quantity: parseInt(e.target.value) || 0,
                    })
                  }
                />
              </FormControl>

              {formData.orderType !== 'MARKET' && (
                <FormControl>
                  <FormLabel>
                    {formData.orderType === 'LIMIT' ? 'Limit' : 'Stop'} Price
                  </FormLabel>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.price}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        price: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </FormControl>
              )}

              <Button
                colorScheme={formData.side === 'BUY' ? 'green' : 'red'}
                isLoading={placing}
                onClick={handlePlaceOrder}
                size="lg"
              >
                {formData.side} {formData.quantity} shares
              </Button>
            </Flex>
          </CardBody>
        </Card>

        {/* Quick Stats */}
        <Card>
          <CardHeader>
            <Heading size="md">Portfolio Status</Heading>
          </CardHeader>
          <CardBody>
            <Flex direction="column" gap={4}>
              <Box>
                <FormLabel>Open Positions</FormLabel>
                <Heading size="lg">{positions.length}</Heading>
              </Box>
              <Box>
                <FormLabel>Pending Orders</FormLabel>
                <Heading size="lg">
                  {orders.filter((o) => o.status === 'PENDING').length}
                </Heading>
              </Box>
              <Box>
                <FormLabel>Total Filled</FormLabel>
                <Heading size="lg">
                  {orders.filter((o) => o.status === 'FILLED').length}
                </Heading>
              </Box>
            </Flex>
          </CardBody>
        </Card>
      </Grid>

      {/* Quant Signals Panel */}
      <Card mb={8}>
        <CardHeader>
          <Flex justify="space-between" align="center">
            <Heading size="md">Quant Signals</Heading>
            <Tooltip label="Refresh signals">
              <Button size="sm" isLoading={loadingSignals} onClick={fetchSignals} variant="ghost">
                Refresh
              </Button>
            </Tooltip>
          </Flex>
        </CardHeader>
        <CardBody>
          {signals.length > 0 ? (
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>Ticker</Th>
                  <Th>Model</Th>
                  <Th>Signal</Th>
                  <Th isNumeric>Confidence</Th>
                  <Th>Generated</Th>
                  <Th>Action</Th>
                </Tr>
              </Thead>
              <Tbody>
                {signals.map((sig, idx) => (
                  <Tr key={idx}>
                    <Td fontWeight="bold">{sig.ticker}</Td>
                    <Td fontSize="sm" color="gray.600">{sig.model_name}</Td>
                    <Td>
                      <Badge
                        colorScheme={
                          sig.signal === 'BUY' ? 'green' : sig.signal === 'SELL' ? 'red' : 'gray'
                        }
                        fontSize="sm"
                        px={3}
                        py={1}
                      >
                        {sig.signal}
                      </Badge>
                    </Td>
                    <Td isNumeric>
                      <Text color={sig.confidence >= 0.7 ? 'green.600' : 'orange.500'}>
                        {(sig.confidence * 100).toFixed(1)}%
                      </Text>
                    </Td>
                    <Td fontSize="xs" color="gray.500">
                      {new Date(sig.generated_at).toLocaleTimeString()}
                    </Td>
                    <Td>
                      {sig.signal !== 'HOLD' && (
                        <Button
                          size="xs"
                          colorScheme={sig.signal === 'BUY' ? 'green' : 'red'}
                          onClick={() =>
                            setFormData((prev) => ({
                              ...prev,
                              symbol: sig.ticker,
                              side: sig.signal as 'BUY' | 'SELL',
                              orderType: 'MARKET',
                            }))
                          }
                        >
                          {sig.signal}
                        </Button>
                      )}
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          ) : (
            <Text color="gray.500" fontSize="sm">
              {loadingSignals ? 'Loading signals...' : 'No signals yet — train a model in Research to generate signals.'}
            </Text>
          )}
        </CardBody>
      </Card>

      {/* Positions Table */}
      <Card mb={8}>
        <CardHeader>
          <Heading size="md">Open Positions</Heading>
        </CardHeader>
        <CardBody>
          {positions.length > 0 ? (
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>Symbol</Th>
                  <Th isNumeric>Qty</Th>
                  <Th isNumeric>Entry Price</Th>
                  <Th isNumeric>Current Price</Th>
                  <Th isNumeric>P&L %</Th>
                </Tr>
              </Thead>
              <Tbody>
                {positions.map((pos) => (
                  <Tr key={pos.symbol}>
                    <Td fontWeight="bold">{pos.symbol}</Td>
                    <Td isNumeric>{pos.quantity}</Td>
                    <Td isNumeric>${pos.entry_price.toFixed(2)}</Td>
                    <Td isNumeric>${pos.current_price.toFixed(2)}</Td>
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

      {/* Orders Table */}
      <Card>
        <CardHeader>
          <Heading size="md">Recent Orders</Heading>
        </CardHeader>
        <CardBody>
          {orders.length > 0 ? (
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>Symbol</Th>
                  <Th>Side</Th>
                  <Th isNumeric>Qty</Th>
                  <Th isNumeric>Price</Th>
                  <Th>Status</Th>
                  <Th>Time</Th>
                </Tr>
              </Thead>
              <Tbody>
                {orders.map((order) => (
                  <Tr key={order.order_id}>
                    <Td fontWeight="bold">{order.symbol}</Td>
                    <Td>
                      <Badge colorScheme={order.side === 'BUY' ? 'green' : 'red'}>
                        {order.side}
                      </Badge>
                    </Td>
                    <Td isNumeric>{order.quantity}</Td>
                    <Td isNumeric>${order.price.toFixed(2)}</Td>
                    <Td>
                      <Badge
                        colorScheme={
                          order.status === 'FILLED'
                            ? 'green'
                            : order.status === 'PENDING'
                            ? 'yellow'
                            : 'red'
                        }
                      >
                        {order.status}
                      </Badge>
                    </Td>
                    <Td fontSize="sm">{new Date(order.timestamp).toLocaleTimeString()}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          ) : (
            <Heading size="sm" color="gray.500">
              No orders yet
            </Heading>
          )}
        </CardBody>
      </Card>
    </Container>
  )
}

export default Trading
