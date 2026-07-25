#pragma once

#include <cstdint>

namespace md_gateway {

struct CtpShmTickRecord {
    char symbol[32];
    std::uint64_t symbol_id;
    std::uint32_t trading_day;
    std::uint64_t update_time;

    double last_price;
    int volume;
    double turnover;
    double open_interest;

    double upper_limit;
    double lower_limit;
    double open_price;
    double highest_price;
    double lowest_price;
    double pre_close_price;
    double pre_settlement_price;
    std::uint8_t settlement_price_valid;
    double settlement_price;

    double bid_price[5];
    int bid_volume[5];
    double ask_price[5];
    int ask_volume[5];
};

}  // namespace md_gateway
