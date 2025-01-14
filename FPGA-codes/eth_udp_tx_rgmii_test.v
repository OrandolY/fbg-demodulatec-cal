/////////////////////////////////////////////////////////////////////////////////
// Company: 武汉芯路恒科技有限公司
// Engineer: Max
// Web: www.corecourse.cn
// 
// Create Date: 2020/07/20 00:00:00
// Design Name: eth_udp_tx_gmii_test
// Module Name: eth_udp_tx_gmii_test
// Project Name: eth_udp_tx_gmii_test
// Target Devices: XC7A35T-2FGG484I
// Tool Versions: Vivado 2018.3
// Description: eth_udp_tx_gmii模块顶层测试文件
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////

`timescale 1ns / 1ps
`define CLK_PERIOD 8

module eth_udp_tx_rgmii_test(
	clk50M,
	reset_n,
	led,
	eth_reset_n,
	rgmii_tx_clk,	
	rgmii_txd,
	rgmii_txen
);
    input         clk50M;
    input         reset_n;
    output        led;
    output        eth_reset_n;
    output        rgmii_tx_clk;
    output  [3:0] rgmii_txd;
    output        rgmii_txen;
    
    wire gmii_tx_clk;
    wire [7:0] gmii_txd;
    wire gmii_txen;

    wire       clk125M;
    wire       udp_gmii_rst_n;
    wire       pll_locked;
    reg [27:0] cnt_dly_time;
    wire       tx_en_pulse;
    wire       tx_done;  
    wire       payload_req;
    wire [7:0]  payload_dat;
    reg [15:0] tx_byte_cnt;

    assign led            = pll_locked;
    assign eth_reset_n    = pll_locked;
    assign udp_gmii_rst_n = pll_locked;
    
    wire clk8M;
    
  pll pll
   (
    // Clock out ports
    .clk_out1(clk125M),     // output clk_out1
    .clk_out2(clk8M),     // output clk_out2
    // Status and control signals
    .resetn(reset_n), // input resetn
    .locked(pll_locked),       // output locked
   // Clock in ports
    .clk_in1(clk50M));      // input clk_in1

    wire fifo_wr_clk;
    wire fifo_rd_clk;
    reg  [15:0]fbg_cnt = 16'h1;
    wire [15:0]fbg_data;
    wire fifo_wr_en;
    wire fifo_rd_en;
    wire fifo_full;
    wire fifo_empty;
    
    reg [31:0]cnt_div_clk = 0;
    reg clk1khz_fluse = 1'b0;
    reg clk1khz = 1'b0;
    /*
    assign fifo_wr_clk = clk1khz;//clk8M;
    assign fifo_rd_clk = clk125M;
    assign fifo_wr_en = ~fifo_full;
    assign fifo_rd_en = ~fifo_empty & payload_req;
    */
    assign tx_en_pulse = clk1khz_fluse;
    
    reg  [31:0]header_num = 32'h00_00_00_00;
    
    always@(posedge clk50M)
        if(clk1khz_fluse && header_num == 32'h06_06_06_06)
            header_num <= 32'h01_01_01_01;
        else if(clk1khz_fluse)
            header_num <= header_num + 32'h01_01_01_01;
        else
            header_num <= header_num;
    
    always@(posedge clk50M)
        if(cnt_div_clk == 32'd12_499)// 249_999 == 60ms / 6package(whole msg)
            begin
                cnt_div_clk <= 0;
                clk1khz_fluse <= 1'b1;
            end
        else
            begin
                cnt_div_clk <= cnt_div_clk + 1'b1;
                clk1khz_fluse <= 1'b0;
            end

    reg  [15:0]wr_addr_fbg = 0;
    reg  [15:0]wr_data_fbg = 0;
    
    reg  [63:0]buf_to_send = 64'hff_ff_ff_ff_01_01_01_01;
    
    assign payload_dat = buf_to_send[7:0];
    
    always@(posedge clk125M)
        if(~payload_req)
            begin
                buf_to_send <= {32'hff_ff_ff_ff, header_num};
            end
        else if(buf_to_send[63:32] == 32'hff_ff_ff_ff && payload_req)
            begin
                buf_to_send <= {8'hff, fbg_data[15:8], fbg_data[7:0], fbg_cnt[15:8], fbg_cnt[7:0], buf_to_send[31:8]};
            end
        else if(payload_req)
            begin
                buf_to_send <= {8'hff, buf_to_send[63:8]};
            end
    
    always@(posedge clk125M)
        if(buf_to_send[63:32] == 32'hff_ff_ff_ff && payload_req && fbg_cnt == 1800)
            begin
                fbg_cnt <= 1;
            end
        else if(buf_to_send[63:32] == 32'hff_ff_ff_ff && tx_done && fbg_cnt > 1)
            begin
                fbg_cnt <= fbg_cnt - 1;
            end
        else if(buf_to_send[63:32] == 32'hff_ff_ff_ff && payload_req)
            begin
                fbg_cnt <= fbg_cnt + 1;
            end
    
    data_save ram_fbg_data (
      .clka(clk8M),    // input wire clka
      .wea(0),      // input wire [0 : 0] wea
      .addra(wr_addr_fbg),  // input wire [10 : 0] addra
      .dina(wr_data_fbg),    // input wire [15 : 0] dina
      .enb(1),      // input wire enb
      .clkb(clk125M),    // input wire clkb
      .addrb(fbg_cnt[10 : 0]),  // input wire [10 : 0] addrb
      .doutb(fbg_data)  // output wire [15 : 0] doutb
    );
   
/*
    fifo fifo0 (
    .wr_clk(fifo_wr_clk),  // input wire wr_clk
    .rd_clk(fifo_rd_clk),  // input wire rd_clk
    .din({fbg_cnt[7:0], fbg_cnt[15:8],fbg_data[7:0], fbg_data[15:8]}),        // input wire [31 : 0] din
    .wr_en(fifo_wr_en),    // input wire wr_en
    .rd_en(fifo_rd_en),    // input wire rd_en
    .dout(payload_dat),      // output wire [7 : 0] dout
    .full(fifo_full),      // output wire full
    .empty(fifo_empty)    // output wire empty
    );
*/
    eth_udp_tx_gmii eth_udp_tx_gmii
    (
        .clk125m       (clk125M               ),
        .reset_n       (udp_gmii_rst_n        ),
                       
        .tx_en_pulse   (tx_en_pulse           ),
        .tx_done       (tx_done               ),
                       
        .dst_mac       (48'hdc_a6_32_1a_d4_10 ),//raspi
        //.dst_mac       (48'h08_26_AE_35_A0_32 ),//PC mac 08_26_AE_35_A0_32
        .src_mac       (48'h00_0a_35_01_fe_c0 ),  
        //.dst_ip        (32'hc0_a8_00_03       ),//PC
        .dst_ip        (32'hc0_a8_00_04       ),
        .src_ip        (32'hc0_a8_00_02       ),
        .dst_port      (16'd2599              ),
        .src_port      (16'd2599              ),
                       
        .data_length   (1204      ),

        .payload_req_o (payload_req           ),
        .payload_dat_i (payload_dat           ),

        .gmii_tx_clk   (gmii_tx_clk           ),	
        .gmii_txen     (gmii_txen             ),
        .gmii_txd      (gmii_txd              )
    );

     gmii_to_rgmii gmii_to_rgmii(
      .reset_n(udp_gmii_rst_n),

      .gmii_tx_clk(gmii_tx_clk),
      .gmii_txd(gmii_txd),
      .gmii_txen(gmii_txen),
      .gmii_txer(1'b0),

      .rgmii_tx_clk(rgmii_tx_clk),
      .rgmii_txd(rgmii_txd),
      .rgmii_txen(rgmii_txen)
    );

    

endmodule
