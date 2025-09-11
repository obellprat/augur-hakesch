/*
  Warnings:

  - You are about to drop the column `TB_start` on the `NAM` table. All the data in the column will be lost.
  - You are about to drop the column `catchment_area` on the `NAM` table. All the data in the column will be lost.
  - You are about to drop the column `channel_length` on the `NAM` table. All the data in the column will be lost.
  - You are about to drop the column `curve_number` on the `NAM` table. All the data in the column will be lost.
  - You are about to drop the column `delta_h` on the `NAM` table. All the data in the column will be lost.
  - You are about to drop the column `istep` on the `NAM` table. All the data in the column will be lost.
  - You are about to drop the column `max_iter` on the `NAM` table. All the data in the column will be lost.
  - You are about to drop the column `tol` on the `NAM` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "NAM" DROP COLUMN "TB_start",
DROP COLUMN "catchment_area",
DROP COLUMN "channel_length",
DROP COLUMN "curve_number",
DROP COLUMN "delta_h",
DROP COLUMN "istep",
DROP COLUMN "max_iter",
DROP COLUMN "tol",
ADD COLUMN     "precipitation_factor" DOUBLE PRECISION NOT NULL DEFAULT 1.0,
ADD COLUMN     "routing_method" TEXT NOT NULL DEFAULT 'time_values',
ADD COLUMN     "storm_center_mode" TEXT NOT NULL DEFAULT 'centroid',
ADD COLUMN     "water_balance_mode" TEXT NOT NULL DEFAULT 'simple';

-- AlterTable
ALTER TABLE "NAM_Result" ADD COLUMN     "effective_curve_number" DOUBLE PRECISION;

-- CreateTable
CREATE TABLE "WaterBalanceMode" (
    "mode" TEXT NOT NULL,
    "description" TEXT NOT NULL,

    CONSTRAINT "WaterBalanceMode_pkey" PRIMARY KEY ("mode")
);

-- CreateTable
CREATE TABLE "StormCenterMode" (
    "mode" TEXT NOT NULL,
    "description" TEXT NOT NULL,

    CONSTRAINT "StormCenterMode_pkey" PRIMARY KEY ("mode")
);

-- CreateTable
CREATE TABLE "RoutingMethod" (
    "method" TEXT NOT NULL,
    "description" TEXT NOT NULL,

    CONSTRAINT "RoutingMethod_pkey" PRIMARY KEY ("method")
);

-- AddForeignKey
ALTER TABLE "NAM" ADD CONSTRAINT "NAM_water_balance_mode_fkey" FOREIGN KEY ("water_balance_mode") REFERENCES "WaterBalanceMode"("mode") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NAM" ADD CONSTRAINT "NAM_storm_center_mode_fkey" FOREIGN KEY ("storm_center_mode") REFERENCES "StormCenterMode"("mode") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NAM" ADD CONSTRAINT "NAM_routing_method_fkey" FOREIGN KEY ("routing_method") REFERENCES "RoutingMethod"("method") ON DELETE RESTRICT ON UPDATE CASCADE;
