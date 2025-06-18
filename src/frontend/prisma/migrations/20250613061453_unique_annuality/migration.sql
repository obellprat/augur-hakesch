/*
  Warnings:

  - A unique constraint covering the columns `[number]` on the table `Annualities` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "Annualities_number_key" ON "Annualities"("number");
