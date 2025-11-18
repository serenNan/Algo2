/* Copyright (C) 2024 Hong Kong University of Science and Technology

This repository is used for the Computer Networks (ELEC 3120) 
course taught at Hong Kong University of Science and Technology. 

No part of the project may be copied and/or distributed without 
the express permission of the course staff. Everyone is prohibited 
from releasing their forks in any public places. */

/**
 * This file implements helper functions to create and manipulate packets.
 *
 * Do NOT modify this file.
 */

#include <arpa/inet.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "foggy_packet.h"

uint16_t get_src(foggy_tcp_header_t* header) {
  return ntohs(header->source_port);
}

uint16_t get_dst(foggy_tcp_header_t* header) {
  return ntohs(header->destination_port);
}

uint32_t get_seq(foggy_tcp_header_t* header) {
  return ntohl(header->seq_num);
}

uint32_t get_ack(foggy_tcp_header_t* header) {
  return ntohl(header->ack_num);
}

uint16_t get_hlen(foggy_tcp_header_t* header) {
  return ntohs(header->hlen);
}

uint16_t get_plen(foggy_tcp_header_t* header) {
  return ntohs(header->plen);
}

uint8_t get_flags(foggy_tcp_header_t* header) {
  return header->flags;
}

uint16_t get_advertised_window(foggy_tcp_header_t* header) {
  return ntohs(header->advertised_window);
}

uint16_t get_extension_length(foggy_tcp_header_t* header) {
  return ntohs(header->extension_length);
}

uint8_t* get_extension_data(foggy_tcp_header_t* header) {
  return (uint8_t*)(header + 1);
}

void set_src(foggy_tcp_header_t* header, uint16_t src) {
  header->source_port = htons(src);
}

void set_dst(foggy_tcp_header_t* header, uint16_t dst) {
  header->destination_port = htons(dst);
}

void set_seq(foggy_tcp_header_t* header, uint32_t seq) {
  header->seq_num = htonl(seq);
}

void set_ack(foggy_tcp_header_t* header, uint32_t ack) {
  header->ack_num = htonl(ack);
}

void set_hlen(foggy_tcp_header_t* header, uint16_t hlen) {
  header->hlen = htons(hlen);
}

void set_plen(foggy_tcp_header_t* header, uint16_t plen) {
  header->plen = htons(plen);
}

void set_flags(foggy_tcp_header_t* header, uint8_t flags) {
  header->flags = flags;
}

void set_advertised_window(foggy_tcp_header_t* header, uint16_t adv_window) {
  header->advertised_window = htons(adv_window);
}

void set_extension_length(foggy_tcp_header_t* header, uint16_t ext) {
  header->extension_length = htons(ext);
}

void set_extension_data(foggy_tcp_header_t* header, uint8_t* ext_data) {
  memcpy(header->extension_data, ext_data, get_extension_length(header));
}

void set_header(foggy_tcp_header_t* header,
                uint16_t src,
                uint16_t dst,
                uint32_t seq,
                uint32_t ack,
                uint16_t hlen,
                uint16_t plen,
                uint8_t flags,
                uint16_t adv_window,
                uint16_t ext,
                uint8_t* ext_data) {
  header->identifier = htonl(IDENTIFIER);
  header->source_port = htons(src);
  header->destination_port = htons(dst);
  header->seq_num = htonl(seq);
  header->ack_num = htonl(ack);
  header->hlen = htons(hlen);
  header->plen = htons(plen);
  header->flags = flags;
  header->advertised_window = htons(adv_window);
  header->extension_length = htons(ext);

  memcpy(header->extension_data, ext_data, ext);
}

uint8_t* get_payload(uint8_t* pkt) {
  foggy_tcp_header_t* header = (foggy_tcp_header_t*)pkt;
  uint16_t ext_len = get_extension_length(header);
  int offset = sizeof(foggy_tcp_header_t) + ext_len;
  return (uint8_t*)header + offset;
}

uint16_t get_payload_len(uint8_t* pkt) {
  foggy_tcp_header_t* header = (foggy_tcp_header_t*)pkt;
  return get_plen(header) - get_hlen(header);
}

void set_payload(uint8_t* pkt, uint8_t* payload, uint16_t payload_len) {
  foggy_tcp_header_t* header = (foggy_tcp_header_t*)pkt;
  uint16_t ext_len = get_extension_length(header);
  int offset = sizeof(foggy_tcp_header_t) + ext_len;
  memcpy((uint8_t*)header + offset, payload, payload_len);
}

uint8_t* create_packet(uint16_t src,
                       uint16_t dst,
                       uint32_t seq,
                       uint32_t ack,
                       uint16_t hlen,
                       uint16_t plen,
                       uint8_t flags,
                       uint16_t adv_window,
                       uint16_t ext_len,
                       uint8_t* ext_data,
                       uint8_t* payload,
                       uint16_t payload_len) {
  if (hlen < sizeof(foggy_tcp_header_t)) {
    return NULL;
  }
  if (plen < hlen) {
    return NULL;
  }

  uint8_t* packet = (uint8_t*)malloc(sizeof(foggy_tcp_header_t) + payload_len);
  if (packet == NULL) {
    return NULL;
  }

  foggy_tcp_header_t* header = (foggy_tcp_header_t*)packet;
  set_header(header, src, dst, seq, ack, hlen, plen, flags, adv_window, ext_len,
             ext_data);

  uint8_t* pkt_payload = get_payload(packet);
  memcpy(pkt_payload, payload, payload_len);

  return packet;
}
