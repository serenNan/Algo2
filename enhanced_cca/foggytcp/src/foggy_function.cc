/* Copyright (C) 2024 Hong Kong University of Science and Technology

This repository is used for the Computer Networks (ELEC 3120) 
course taught at Hong Kong University of Science and Technology. 

No part of the project may be copied and/or distributed without 
the express permission of the course staff. Everyone is prohibited 
from releasing their forks in any public places. */

#include <deque>
#include <cstdlib>
#include <cstring>
#include <cstdio>

#include "foggy_function.h"
#include "foggy_backend.h"


#define MIN(X, Y) (((X) < (Y)) ? (X) : (Y))
#define MAX(X, Y) (((X) > (Y)) ? (X) : (Y))

#define DEBUG_PRINT 1
#define debug_printf(fmt, ...)                            \
  do {                                                    \
    if (DEBUG_PRINT) fprintf(stdout, fmt, ##__VA_ARGS__); \
  } while (0)


void on_recv_pkt(foggy_socket_t *sock, uint8_t *pkt) {
  debug_printf("Received packet\n");
  foggy_tcp_header_t *hdr = (foggy_tcp_header_t *)pkt;
  uint8_t flags = get_flags(hdr);

  switch (flags) {
    case ACK_FLAG_MASK: {
      uint32_t ack = get_ack(hdr);
      printf("Receive ACK %d\n", ack);
      sock->window.advertised_window = get_advertised_window(hdr);
      handle_ack(sock, ack);
      break; 
    }

    default: {
      if (get_payload_len(pkt) > 0) {
        debug_printf("Received data packet %d %d\n", get_seq(hdr),
                     get_seq(hdr) + get_payload_len(pkt));

        sock->window.advertised_window = get_advertised_window(hdr);
        add_receive_window(sock, pkt);
        process_receive_window(sock);
        debug_printf("Sending ACK packet %d\n", sock->window.next_seq_expected);

        uint8_t *ack_pkt = create_packet(
            sock->my_port, ntohs(sock->conn.sin_port),
            sock->window.last_byte_sent, sock->window.next_seq_expected,
            sizeof(foggy_tcp_header_t), sizeof(foggy_tcp_header_t), ACK_FLAG_MASK,
            MAX(MAX_NETWORK_BUFFER - (uint32_t)sock->received_len, MSS), 0,
            NULL, NULL, 0);
        sendto(sock->socket, ack_pkt, sizeof(foggy_tcp_header_t), 0,
               (struct sockaddr *)&(sock->conn), sizeof(sock->conn));
        free(ack_pkt);
      }
    }
  }
}

void send_pkts(foggy_socket_t *sock, uint8_t *data, int buf_len) {
  uint8_t *data_offset = data;
  transmit_send_window(sock);

  if (buf_len > 0) {
    while (buf_len != 0) {
      uint16_t payload_len = MIN(buf_len, (int)MSS);

      send_window_slot_t slot;
      slot.is_sent = 0;
      slot.msg = create_packet(
          sock->my_port, ntohs(sock->conn.sin_port),
          sock->window.last_byte_sent, sock->window.next_seq_expected,
          sizeof(foggy_tcp_header_t), sizeof(foggy_tcp_header_t) + payload_len,
          ACK_FLAG_MASK,
          MAX(MAX_NETWORK_BUFFER - (uint32_t)sock->received_len, MSS), 0, NULL,
          data_offset, payload_len);
      sock->send_window.push_back(slot);

      buf_len -= payload_len;
      data_offset += payload_len;
      sock->window.last_byte_sent += payload_len;
    }
  }
  receive_send_window(sock);
}


void add_receive_window(foggy_socket_t *sock, uint8_t *pkt) {
  foggy_tcp_header_t *hdr = (foggy_tcp_header_t *)pkt;
  uint32_t seq = get_seq(hdr);

  if (before(seq, sock->window.next_seq_expected)) {
    return;
  }

  uint32_t offset = seq - sock->window.next_seq_expected;
  uint32_t slot_index = offset / MSS;

  if (slot_index >= RECEIVE_WINDOW_SLOT_SIZE) {
    return;
  }

  receive_window_slot_t *cur_slot = &(sock->receive_window[slot_index]);
  if (cur_slot->is_used == 0) {
    cur_slot->is_used = 1;
    cur_slot->msg = (uint8_t*) malloc(get_plen(hdr));
    memcpy(cur_slot->msg, pkt, get_plen(hdr));
  }
}

void process_receive_window(foggy_socket_t *sock) {
  while (1) {
    receive_window_slot_t *cur_slot = &(sock->receive_window[0]);

    if (cur_slot->is_used == 0) break;

    foggy_tcp_header_t *hdr = (foggy_tcp_header_t *)cur_slot->msg;

    if (get_seq(hdr) != sock->window.next_seq_expected) break;

    uint16_t payload_len = get_payload_len(cur_slot->msg);
    sock->window.next_seq_expected += payload_len;

    sock->received_buf = (uint8_t*)
        realloc(sock->received_buf, sock->received_len + payload_len);
    memcpy(sock->received_buf + sock->received_len, get_payload(cur_slot->msg),
           payload_len);
    sock->received_len += payload_len;

    cur_slot->is_used = 0;
    free(cur_slot->msg);
    cur_slot->msg = NULL;

    for (int i = 1; i < RECEIVE_WINDOW_SLOT_SIZE; i++) {
      sock->receive_window[i - 1] = sock->receive_window[i];
    }

    sock->receive_window[RECEIVE_WINDOW_SLOT_SIZE - 1].is_used = 0;
    sock->receive_window[RECEIVE_WINDOW_SLOT_SIZE - 1].msg = NULL;
  }
}

void transmit_send_window(foggy_socket_t *sock) {
  if (sock->send_window.empty()) return;

  uint32_t effective_window = MIN(sock->window.congestion_window,
                                   sock->window.advertised_window);

  uint32_t bytes_in_flight = 0;
  for (auto& slot : sock->send_window) {
    if (slot.is_sent) {
      foggy_tcp_header_t *hdr = (foggy_tcp_header_t *)slot.msg;
      if (!has_been_acked(sock, get_seq(hdr))) {
        bytes_in_flight += get_payload_len(slot.msg);
      }
    }
  }

  for (auto& slot : sock->send_window) {
    if (slot.is_sent) continue;

    foggy_tcp_header_t *hdr = (foggy_tcp_header_t *)slot.msg;
    uint16_t payload_len = get_payload_len(slot.msg);

    if (bytes_in_flight + payload_len <= effective_window) {
      debug_printf("Sending packet %d %d\n", get_seq(hdr),
                   get_seq(hdr) + payload_len);
      slot.is_sent = 1;
      sendto(sock->socket, slot.msg, get_plen(hdr), 0,
            (struct sockaddr *)&(sock->conn), sizeof(sock->conn));
      bytes_in_flight += payload_len;
    } else {
      break;
    }
  }
}

void receive_send_window(foggy_socket_t *sock) {
  while (1) {
    if (sock->send_window.empty()) break;

    send_window_slot_t slot = sock->send_window.front();
    foggy_tcp_header_t *hdr = (foggy_tcp_header_t *)slot.msg;

    if (slot.is_sent == 0) {
      break;
    }
    if (has_been_acked(sock, get_seq(hdr)) == 0) {
      break;
    }
    sock->send_window.pop_front();
    free(slot.msg);
  }
}

void handle_ack(foggy_socket_t *sock, uint32_t ack) {
  if (ack == sock->window.last_ack_received) {
    sock->window.dup_ack_count++;
    debug_printf("Duplicate ACK count: %d\n", sock->window.dup_ack_count);

    if (sock->window.dup_ack_count == 3) {
      debug_printf("Fast retransmit triggered\n");

      sock->window.ssthresh = MAX(sock->window.congestion_window / 2, MSS);
      sock->window.congestion_window = sock->window.ssthresh + 3 * MSS;
      sock->window.reno_state = RENO_FAST_RECOVERY;

      for (auto& slot : sock->send_window) {
        foggy_tcp_header_t *hdr = (foggy_tcp_header_t *)slot.msg;
        if (!has_been_acked(sock, get_seq(hdr))) {
          debug_printf("Retransmitting packet %d\n", get_seq(hdr));
          sendto(sock->socket, slot.msg, get_plen(hdr), 0,
                (struct sockaddr *)&(sock->conn), sizeof(sock->conn));
          break;
        }
      }
    } else if (sock->window.reno_state == RENO_FAST_RECOVERY && sock->window.dup_ack_count > 3) {
      sock->window.congestion_window += MSS;
    }
  } else if (after(ack, sock->window.last_ack_received)) {
    sock->window.dup_ack_count = 0;

    if (sock->window.reno_state == RENO_FAST_RECOVERY) {
      sock->window.congestion_window = sock->window.ssthresh;
      sock->window.reno_state = RENO_CONGESTION_AVOIDANCE;
      debug_printf("Exiting Fast Recovery, CWND: %d\n", sock->window.congestion_window);
    } else if (sock->window.reno_state == RENO_SLOW_START) {
      sock->window.congestion_window += MSS;
      debug_printf("Slow Start, CWND: %d\n", sock->window.congestion_window);

      if (sock->window.congestion_window >= sock->window.ssthresh) {
        sock->window.reno_state = RENO_CONGESTION_AVOIDANCE;
        debug_printf("Entering Congestion Avoidance\n");
      }
    } else if (sock->window.reno_state == RENO_CONGESTION_AVOIDANCE) {
      sock->window.congestion_window += (MSS * MSS) / sock->window.congestion_window;
      debug_printf("Congestion Avoidance, CWND: %d\n", sock->window.congestion_window);
    }

    sock->window.last_ack_received = ack;
  }
}
