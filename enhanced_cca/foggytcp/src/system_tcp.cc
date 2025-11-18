/**
 * Copyright (C) 2024 Hong Kong University of Science and Technology
 *
 * This repository is used for the Computer Networks (ELEC 3120) course taught
 * at Hong Kong University of Science and Technology.
 *
 * No part of the project may be copied and/or distributed without the express
 * permission of the course staff. Everyone is prohibited from releasing their
 * forks in any public places.
 */

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cstdio>

#include "foggy_tcp.h"

struct system_socket {
  int init_sock_fd;
  int accept_sock_fd;
  foggy_socket_type_t socket_type;
};

void* foggy_socket(const foggy_socket_type_t socket_type,
                   const char* server_port,
                   const char* server_ip) {
  struct system_socket* sock = new system_socket{0};
  sock->socket_type = socket_type;
  sock->init_sock_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (sock->init_sock_fd < 0) {
    perror("ERROR opening socket");
    return NULL;
  }

  int portno = (uint16_t)atoi(server_port);

  sockaddr_in serverAddress;
  serverAddress.sin_family = AF_INET;
  serverAddress.sin_port = htons(portno);
  serverAddress.sin_addr.s_addr = inet_addr(server_ip);

  if (socket_type == TCP_LISTENER) {
    bind(sock->init_sock_fd, (struct sockaddr*)&serverAddress,
         sizeof(serverAddress));
    listen(sock->init_sock_fd, 5);
    sock->accept_sock_fd = accept(sock->init_sock_fd, NULL, NULL);
  } else {
    connect(sock->init_sock_fd, (struct sockaddr*)&serverAddress,
            sizeof(serverAddress));
  }
  return (void*)sock;
}

int foggy_close(void* in_sock) {
  struct system_socket* sock = (struct system_socket*)in_sock;
  return close(sock->init_sock_fd);
}

int foggy_read(void* in_sock, void* buf, const int length) {
  struct system_socket* sock = (struct system_socket*)in_sock;
  int sock_fd = sock->socket_type == TCP_LISTENER
                    ? sock->accept_sock_fd
                    : sock->init_sock_fd;
  return read(sock_fd, buf, length);
}

int foggy_write(void* in_sock, const void* buf, const int length) {
  struct system_socket* sock = (struct system_socket*)in_sock;
  int sock_fd = sock->socket_type == TCP_LISTENER
                    ? sock->accept_sock_fd
                    : sock->init_sock_fd;
  return write(sock_fd, buf, length);
}