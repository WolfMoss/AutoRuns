/*
 Navicat Premium Data Transfer

 Source Server         : 10.10.10.5
 Source Server Type    : MySQL
 Source Server Version : 80200
 Source Host           : axiba.idnmd.top:8306
 Source Schema         : quant

 Target Server Type    : MySQL
 Target Server Version : 80200
 File Encoding         : 65001

 Date: 26/11/2024 22:53:36
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for pcr
-- ----------------------------
DROP TABLE IF EXISTS `pcr`;
CREATE TABLE `pcr`  (
  `SECURITY_CODE` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '标的代码',
  `TRADE_DATE` date NOT NULL COMMENT '日期',
  `SECURITY_ABBR` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标的名称',
  `LEAVES_CALL_QTY` int(0) NULL DEFAULT NULL COMMENT '看涨持仓量',
  `LEAVES_PUT_QTY` int(0) NULL DEFAULT NULL COMMENT '看跌持仓量',
  `PC_RATE` float NULL DEFAULT NULL COMMENT 'PCR=看跌/看涨',
  PRIMARY KEY (`SECURITY_CODE`, `TRADE_DATE`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
