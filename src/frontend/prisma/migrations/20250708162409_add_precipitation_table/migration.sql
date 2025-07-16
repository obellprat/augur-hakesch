-- CreateTable
CREATE TABLE "Precipitation" (
    "id" SERIAL NOT NULL,
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL,
    "data" TEXT NOT NULL,

    CONSTRAINT "Precipitation_pkey" PRIMARY KEY ("id")
);
