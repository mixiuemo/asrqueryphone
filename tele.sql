/*
Navicat MySQL Data Transfer

Source Server         : 本地MYSQL
Source Server Version : 50730
Source Host           : 127.0.0.1:3306
Source Database       : rgt

Target Server Type    : MYSQL
Target Server Version : 50730
File Encoding         : 65001

Date: 2026-04-16 16:18:49
*/

SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Table structure for tele
-- ----------------------------
DROP TABLE IF EXISTS `tele`;
CREATE TABLE `tele` (
  `NUMBER` int(11) NOT NULL AUTO_INCREMENT,
  `CODE` varchar(50) DEFAULT NULL,
  `DEPARTMENT` varchar(50) DEFAULT NULL,
  `USER` varchar(50) DEFAULT NULL,
  `TELE_CODE` varchar(50) DEFAULT NULL,
  `MAP_ID` varchar(255) DEFAULT NULL,
  `X_NUM` double DEFAULT NULL,
  `Y_NUM` double DEFAULT NULL,
  `Con` varchar(50) DEFAULT NULL,
  `Tele_GROUP` int(11) DEFAULT NULL,
  `JOB` varchar(255) DEFAULT NULL,
  `userPY` text,
  `surPY` text,
  `departmentPY` text,
  `surname` text,
  `unitAbbreviation` text,
  `queryPermission` int(11) DEFAULT '0',
  `UNIT` text,
  `PERSONNEL` text,
  `jobPY` text,
  `unitAbbreviationPY` text,
  `telephoneType` varchar(255) DEFAULT NULL,
  `segment` varchar(255) DEFAULT NULL COMMENT '号段',
  `GROUP` varchar(255) DEFAULT NULL COMMENT '编组',
  `AIStatus` int(11) NOT NULL DEFAULT '1' COMMENT '状态：1-人工，0-智能客服',
  `userPY_no_tone` text,
  `surPY_no_tone` text,
  `departmentPY_no_tone` text,
  `unitAbbreviationPY_no_tone` text,
  `jobPY_no_tone` text,
  KEY `NUMBER` (`NUMBER`),
  KEY `tele_code_idx` (`TELE_CODE`),
  KEY `idx_tele_code` (`TELE_CODE`),
  FULLTEXT KEY `idx_tele_ngram` (`TELE_CODE`,`USER`,`DEPARTMENT`) /*!50100 WITH PARSER `ngram` */ 
) ENGINE=MyISAM AUTO_INCREMENT=1272058 DEFAULT CHARSET=utf8;
