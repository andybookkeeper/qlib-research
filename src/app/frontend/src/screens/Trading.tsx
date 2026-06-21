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

const Trading: React.FC = () => {
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [tickers, setTickers] = useState<string[]>([])
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

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [pos, ord, tick] = await Promise.all([
          apiClient.broker.getPositions(),
          apiClient.broker.getOrders(),
          apiClient.market.getTickers(),
        ])
        setPositions(pos.positions || [])
        setOrders(ord.orders || [])
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
        price: formData.price,
        type: formData.orderType,
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
      setPositions(pos.positions || [])
      setOrders(ord.orders || [])
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
