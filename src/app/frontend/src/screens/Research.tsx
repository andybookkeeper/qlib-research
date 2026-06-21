// src/app/frontend/src/screens/Research.tsx
import React, { useState, useEffect } from 'react'
import {
  Container,
  Grid,
  Card,
  CardBody,
  CardHeader,
  Heading,
  FormControl,
  FormLabel,
  Input,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Alert,
  AlertIcon,
  Flex,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  useToast,
  Progress,
} from '@chakra-ui/react'
import { Model } from '../types'
import { apiClient } from '../api/client'

interface TrainingConfig {
  model_name: string
  lookback: number
  forecast_horizon: number
  features: string[]
  test_size: number
}

const Research: React.FC = () => {
  const [models, setModels] = useState<Model[]>([])
  const [indicators, setIndicators] = useState<any>(null)
  const [backtests, setBacktests] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [training, setTraining] = useState(false)
  const [trainProgress, setTrainProgress] = useState(0)
  const [trainConfig, setTrainConfig] = useState<TrainingConfig>({
    model_name: 'lgb_v1',
    lookback: 60,
    forecast_horizon: 5,
    features: ['RSI', 'MACD', 'Bollinger Bands'],
    test_size: 0.2,
  })
  const toast = useToast()

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [mdls, inds, bt] = await Promise.all([
          apiClient.research.listModels(),
          apiClient.features.getIndicators(),
          apiClient.research.getBacktests(),
        ])
        setModels(mdls.models || [])
        setIndicators(inds)
        setBacktests(bt.backtests || [])
      } catch (err) {
        toast({ title: 'Error loading research data', status: 'error' })
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleTrainModel = async () => {
    try {
      setTraining(true)
      setTrainProgress(0)

      // Simulate training progress
      const progressInterval = setInterval(() => {
        setTrainProgress((prev) => Math.min(prev + Math.random() * 30, 90))
      }, 500)

      const result = await apiClient.training.trainModel(trainConfig)

      clearInterval(progressInterval)
      setTrainProgress(100)

      toast({
        title: 'Model Training Complete',
        description: `${result.model_id} - Test Loss: ${result.test_loss.toFixed(4)}`,
        status: 'success',
      })

      // Refresh models
      const mdls = await apiClient.research.listModels()
      setModels(mdls.models || [])
    } catch (err) {
      toast({
        title: 'Training failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        status: 'error',
      })
    } finally {
      setTraining(false)
      setTrainProgress(0)
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
        Research & Model Development
      </Heading>

      <Tabs>
        <TabList mb="1em">
          <Tab>Models</Tab>
          <Tab>Training</Tab>
          <Tab>Backtests</Tab>
          <Tab>Features</Tab>
        </TabList>

        <TabPanels>
          {/* Models Tab */}
          <TabPanel>
            <Card>
              <CardHeader>
                <Heading size="md">Trained Models</Heading>
              </CardHeader>
              <CardBody>
                {models && models.length > 0 ? (
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Model Name</Th>
                        <Th>Type</Th>
                        <Th isNumeric>Train Loss</Th>
                        <Th isNumeric>Test Loss</Th>
                        <Th isNumeric>Samples</Th>
                        <Th>Trained</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {models.map((model) => (
                        <Tr key={model.name}>
                          <Td fontWeight="bold">{model.name}</Td>
                          <Td>{model.type}</Td>
                          <Td isNumeric>
                            {model.train_loss ? model.train_loss.toFixed(4) : 'N/A'}
                          </Td>
                          <Td isNumeric>
                            {model.test_loss ? model.test_loss.toFixed(4) : 'N/A'}
                          </Td>
                          <Td isNumeric>
                            {model.train_samples + model.test_samples}
                          </Td>
                          <Td fontSize="sm">
                            {new Date(model.trained_at).toLocaleDateString()}
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                ) : (
                  <Heading size="sm" color="gray.500">
                    No trained models yet
                  </Heading>
                )}
              </CardBody>
            </Card>
          </TabPanel>

          {/* Training Tab */}
          <TabPanel>
            <Card>
              <CardHeader>
                <Heading size="md">Train New Model</Heading>
              </CardHeader>
              <CardBody>
                <Flex direction="column" gap={6}>
                  <FormControl>
                    <FormLabel>Model Name</FormLabel>
                    <Input
                      value={trainConfig.model_name}
                      onChange={(e) =>
                        setTrainConfig({
                          ...trainConfig,
                          model_name: e.target.value,
                        })
                      }
                      placeholder="e.g., lgb_v2"
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel>Lookback Period (days)</FormLabel>
                    <Input
                      type="number"
                      value={trainConfig.lookback}
                      onChange={(e) =>
                        setTrainConfig({
                          ...trainConfig,
                          lookback: parseInt(e.target.value) || 60,
                        })
                      }
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel>Forecast Horizon (days)</FormLabel>
                    <Input
                      type="number"
                      value={trainConfig.forecast_horizon}
                      onChange={(e) =>
                        setTrainConfig({
                          ...trainConfig,
                          forecast_horizon: parseInt(e.target.value) || 5,
                        })
                      }
                    />
                  </FormControl>

                  <FormControl>
                    <FormLabel>Test Size</FormLabel>
                    <Input
                      type="number"
                      step="0.05"
                      min="0.1"
                      max="0.5"
                      value={trainConfig.test_size}
                      onChange={(e) =>
                        setTrainConfig({
                          ...trainConfig,
                          test_size: parseFloat(e.target.value) || 0.2,
                        })
                      }
                    />
                  </FormControl>

                  {training && (
                    <>
                      <Alert status="info">
                        <AlertIcon />
                        Training in progress...
                      </Alert>
                      <Progress value={trainProgress} isAnimated />
                    </>
                  )}

                  <Button
                    colorScheme="blue"
                    onClick={handleTrainModel}
                    isLoading={training}
                    isDisabled={training}
                    size="lg"
                  >
                    {training ? `Training... ${trainProgress.toFixed(0)}%` : 'Start Training'}
                  </Button>
                </Flex>
              </CardBody>
            </Card>
          </TabPanel>

          {/* Backtests Tab */}
          <TabPanel>
            <Card>
              <CardHeader>
                <Heading size="md">Backtest Results</Heading>
              </CardHeader>
              <CardBody>
                {backtests && backtests.length > 0 ? (
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Model</Th>
                        <Th>Period</Th>
                        <Th isNumeric>Return %</Th>
                        <Th isNumeric>Sharpe</Th>
                        <Th isNumeric>Max DD %</Th>
                        <Th>Status</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {backtests.map((bt, idx) => (
                        <Tr key={idx}>
                          <Td fontWeight="bold">{bt.model_name}</Td>
                          <Td>{bt.period}</Td>
                          <Td isNumeric color={bt.return_pct >= 0 ? 'green.600' : 'red.600'}>
                            {bt.return_pct?.toFixed(2)}%
                          </Td>
                          <Td isNumeric>{bt.sharpe_ratio?.toFixed(2)}</Td>
                          <Td isNumeric color="red.600">
                            {bt.max_drawdown?.toFixed(2)}%
                          </Td>
                          <Td>
                            <Badge colorScheme="green">Complete</Badge>
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                ) : (
                  <Heading size="sm" color="gray.500">
                    No backtest results yet
                  </Heading>
                )}
              </CardBody>
            </Card>
          </TabPanel>

          {/* Features Tab */}
          <TabPanel>
            <Grid templateColumns="repeat(auto-fit, minmax(300px, 1fr))" gap={6}>
              {indicators ? (
                <>
                  <Card>
                    <CardHeader>
                      <Heading size="sm">Trend Indicators</Heading>
                    </CardHeader>
                    <CardBody>
                      {indicators.trend_indicators?.map((ind: string) => (
                        <Badge key={ind} mr={2} mb={2}>
                          {ind}
                        </Badge>
                      ))}
                    </CardBody>
                  </Card>

                  <Card>
                    <CardHeader>
                      <Heading size="sm">Momentum Indicators</Heading>
                    </CardHeader>
                    <CardBody>
                      {indicators.momentum_indicators?.map((ind: string) => (
                        <Badge key={ind} mr={2} mb={2} colorScheme="purple">
                          {ind}
                        </Badge>
                      ))}
                    </CardBody>
                  </Card>

                  <Card>
                    <CardHeader>
                      <Heading size="sm">Volatility Indicators</Heading>
                    </CardHeader>
                    <CardBody>
                      {indicators.volatility_indicators?.map((ind: string) => (
                        <Badge key={ind} mr={2} mb={2} colorScheme="orange">
                          {ind}
                        </Badge>
                      ))}
                    </CardBody>
                  </Card>

                  <Card>
                    <CardHeader>
                      <Heading size="sm">Volume Indicators</Heading>
                    </CardHeader>
                    <CardBody>
                      {indicators.volume_indicators?.map((ind: string) => (
                        <Badge key={ind} mr={2} mb={2} colorScheme="cyan">
                          {ind}
                        </Badge>
                      ))}
                    </CardBody>
                  </Card>
                </>
              ) : (
                <Heading size="sm" color="gray.500">
                  No indicators available
                </Heading>
              )}
            </Grid>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Container>
  )
}

export default Research
