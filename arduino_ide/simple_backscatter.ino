#include <driver/rmt.h> //rmtの警告は無視でOK

#define RMT_TX_CHANNEL RMT_CHANNEL_0
#define RMT_TX_GPIO GPIO_NUM_4
void init_rmt(){
  rmt_config_t config = {};

  config.rmt_mode = RMT_MODE_TX;
  config.channel = RMT_TX_CHANNEL;
  config.gpio_num = RMT_TX_GPIO;
  config.mem_block_num = 1;

  config.clk_div = 8;

  config.tx_config.loop_en = true;
  config.tx_config.carrier_en = false;
  config.tx_config.idle_output_en = true;
  config.tx_config.idle_level = RMT_IDLE_LEVEL_LOW;

  rmt_config(&config);
  rmt_driver_install(RMT_TX_CHANNEL, 0, 0);
  rmt_item32_t item;
  item.level0 = 1;
  item.level1 = 0;
  item.duration0 = 1;
  item.duration1 = 1;
  // RMTのResolution 10MHz ==> ON, OFF切り替え:5MHz

  rmt_write_items(RMT_TX_CHANNEL, &item, 1, true);
}


void setup() {
  init_rmt();
}

void loop() {
  
}
