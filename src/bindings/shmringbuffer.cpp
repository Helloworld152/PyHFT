#include <pybind11/pybind11.h>

#include <cstdint>
#include <cstring>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_set>

#include "hft_common/ipc/shm_ring_buffer.h"
#include "pyhft/ctp_shm_tick_record.h"

namespace py = pybind11;

namespace {

using Ring = hft_common::ipc::ShmRingBuffer<md_gateway::CtpShmTickRecord>;

py::list to_list(const double (&values)[5]) {
    py::list out;
    for (double value : values) {
        out.append(value);
    }
    return out;
}

py::list to_list(const int (&values)[5]) {
    py::list out;
    for (int value : values) {
        out.append(value);
    }
    return out;
}

py::dict to_dict(const md_gateway::CtpShmTickRecord& tick) {
    char symbol[sizeof(tick.symbol) + 1] {};
    std::memcpy(symbol, tick.symbol, sizeof(tick.symbol));

    py::dict out;
    out["symbol"] = py::str(symbol);
    out["symbol_id"] = tick.symbol_id;
    out["trading_day"] = tick.trading_day;
    out["update_time"] = tick.update_time;
    out["last_price"] = tick.last_price;
    out["volume"] = tick.volume;
    out["turnover"] = tick.turnover;
    out["open_interest"] = tick.open_interest;
    out["upper_limit"] = tick.upper_limit;
    out["lower_limit"] = tick.lower_limit;
    out["open_price"] = tick.open_price;
    out["highest_price"] = tick.highest_price;
    out["lowest_price"] = tick.lowest_price;
    out["pre_close_price"] = tick.pre_close_price;
    out["pre_settlement_price"] = tick.pre_settlement_price;
    out["settlement_price_valid"] = tick.settlement_price_valid != 0;
    out["settlement_price"] = tick.settlement_price;
    out["bid_price"] = to_list(tick.bid_price);
    out["bid_volume"] = to_list(tick.bid_volume);
    out["ask_price"] = to_list(tick.ask_price);
    out["ask_volume"] = to_list(tick.ask_volume);
    return out;
}

class ShmRingBufferReader {
public:
    explicit ShmRingBufferReader(std::string name)
        : name_(std::move(name)),
          ring_(name_, false) {
        const std::uint64_t latest = ring_.latest_seq();
        const std::uint64_t capacity = ring_.get_capacity();
        if (latest == 0 || capacity == 0) {
            next_seq_ = 1;
            return;
        }
        next_seq_ = latest >= capacity ? (latest - capacity + 1) : 1;
    }

    py::list poll(py::object symbol = py::none(), py::object symbols = py::none()) {
        if (closed_) {
            throw std::runtime_error("ShmRingBufferReader is closed");
        }
        if (!symbol.is_none() && !symbols.is_none()) {
            throw std::invalid_argument("symbol and symbols cannot be used together");
        }

        py::list out;
        const std::uint64_t latest = ring_.latest_seq();
        if (latest < next_seq_) {
            return out;
        }

        const std::uint64_t capacity = ring_.get_capacity();
        if (capacity == 0) {
            return out;
        }

        const std::uint64_t earliest = latest >= capacity ? (latest - capacity + 1) : 1;
        if (next_seq_ < earliest) {
            next_seq_ = earliest;
        }

        std::optional<std::unordered_set<std::string>> symbol_filter;
        if (!symbol.is_none()) {
            symbol_filter = std::unordered_set<std::string>{symbol.cast<std::string>()};
        } else if (!symbols.is_none()) {
            symbol_filter.emplace();
            for (const py::handle item : symbols) {
                symbol_filter->insert(py::cast<std::string>(item));
            }
        }

        std::uint64_t seq = next_seq_;
        for (; seq <= latest; ++seq) {
            const auto* msg = ring_.read(seq);
            if (msg == nullptr) {
                continue;
            }
            if (symbol_filter.has_value()) {
                char msg_symbol[sizeof(msg->symbol) + 1] {};
                std::memcpy(msg_symbol, msg->symbol, sizeof(msg->symbol));
                if (!symbol_filter->contains(msg_symbol)) {
                    continue;
                }
            }
            out.append(to_dict(*msg));
        }
        next_seq_ = seq;
        return out;
    }

    void close() {
        if (closed_) {
            return;
        }
        ring_.close();
        closed_ = true;
    }

    bool closed() const noexcept { return closed_; }

private:
    std::string name_;
    Ring ring_;
    std::uint64_t next_seq_ = 1;
    bool closed_ = false;
};

}  // namespace

PYBIND11_MODULE(_shmringbuffer, m) {
    m.doc() = "Python bindings for hft_common::ipc::ShmRingBuffer";

    py::class_<ShmRingBufferReader>(m, "ShmRingBufferReader")
        .def(py::init<std::string>(), py::arg("name"))
        .def(
            "poll",
            &ShmRingBufferReader::poll,
            py::arg("symbol") = py::none(),
            py::arg("symbols") = py::none())
        .def("close", &ShmRingBufferReader::close)
        .def_property_readonly("closed", &ShmRingBufferReader::closed);
}
